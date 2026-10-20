from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from pmem.index.tokenize import tokenize

DEFAULT_ONNX_MODEL = "BAAI/bge-small-zh-v1.5"
LOAD_RETRY_SECONDS = 600.0
_OFFICIAL_HOST = "api.openai.com"
_REMOTE_ENV = "PMEM_EMBED_ALLOW_REMOTE"
_REMOTE_REFUSED = (
    "embedding.base_url 不是本机地址，也不是 https://api.openai.com。"
    "仓库里的配置不能单独打开远程嵌入；要发给其他地址，请在本机设置环境变量 "
    f"{_REMOTE_ENV}=1（且必须是 https），密钥只用 PMEM_OPENAI_API_KEY，不会带上 OPENAI_API_KEY"
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """嵌入请求不跟随跳转，避免本机地址 302 到别处时把正文和密钥一起带过去。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(getattr(req, "full_url", ""), code, "嵌入服务拒绝跟随跳转", headers, fp)


def _loopback(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def embed_url(url: str) -> tuple[str, str] | None:
    """允许的嵌入地址，返回 (去掉末尾斜杠的地址, local / official / remote)。

    本机和官方 OpenAI 地址直接允许。其他地址必须由本机环境变量打开，仓库配置自己写了不算。
    """
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        return None
    if _loopback(host):
        return parsed.geturl().rstrip("/"), "local"
    if host == _OFFICIAL_HOST and parsed.scheme == "https":
        return parsed.geturl().rstrip("/"), "official"
    if os.environ.get(_REMOTE_ENV) == "1" and parsed.scheme == "https":
        return parsed.geturl().rstrip("/"), "remote"
    return None


def _api_key(level: str) -> str:
    """官方地址可以用环境里的 OpenAI 密钥。其他地址只认专供 pmem 的密钥，避免仓库配置把通用密钥带走。"""
    dedicated = os.environ.get("PMEM_OPENAI_API_KEY") or ""
    if level == "official":
        return dedicated or os.environ.get("OPENAI_API_KEY") or ""
    return dedicated


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


class Embedder:
    """把文本转成单位向量；id 用于区分向量缓存。"""

    id = "base"

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """确定性的“假”嵌入：关键词哈希到固定维度，供测试与无模型时的兜底。"""

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.id = f"hash-{dim}"

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in tokenize(text):
                digest = hashlib.md5(token.encode("utf-8")).digest()
                matrix[row, int.from_bytes(digest[:4], "little") % self.dim] += 1.0
        return _normalise(matrix)


class OnnxEmbedder(Embedder):
    def __init__(self, model: str = DEFAULT_ONNX_MODEL, model_path: str = "", cache_dir: Path | None = None):
        from fastembed import TextEmbedding  # 延迟导入：未安装时由 make_embedder 处理

        kwargs = {"model_name": model}
        if model_path:
            kwargs["specific_model_path"] = model_path
        if cache_dir:
            kwargs["cache_dir"] = str(cache_dir)
        self._model = TextEmbedding(**kwargs)
        self.id = f"onnx:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self._model.embed(texts)), dtype=np.float32))


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: float = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaEmbedder(Embedder):
    def __init__(self, model: str, base_url: str = ""):
        self.model = model
        allowed = embed_url(base_url or "http://localhost:11434")
        if allowed is None:
            raise ValueError(_REMOTE_REFUSED)
        self.base_url = allowed[0]
        self.id = f"ollama:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        result = _post_json(f"{self.base_url}/api/embed", {"model": self.model, "input": texts})
        return _normalise(np.array(result["embeddings"], dtype=np.float32))


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str, base_url: str, api_key: str = ""):
        self.model = model
        allowed = embed_url(base_url)
        if allowed is None:
            raise ValueError(_REMOTE_REFUSED)
        self.base_url, level = allowed
        self._api_key = api_key if api_key else _api_key(level)
        self.id = f"openai:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        result = _post_json(f"{self.base_url}/embeddings", {"model": self.model, "input": texts}, headers)
        rows = sorted(result["data"], key=lambda item: item["index"])
        return _normalise(np.array([row["embedding"] for row in rows], dtype=np.float32))


class LazyOnnxEmbedder(Embedder):
    """首次真正需要向量时才加载模型（可能触发下载），避免拖慢不需要语义检索的调用。"""

    def __init__(self, model: str, model_path: str = "", cache_dir: Path | None = None):
        self._args = (model, model_path, cache_dir)
        self._inner: OnnxEmbedder | None = None
        self._failed: tuple[float, Exception] | None = None
        self.id = f"onnx:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._inner is None:
            # 离线时每次重试加载都可能卡在下载上，拖到看门狗超时；冷却期内直接失败，调用方退回关键词检索
            if self._failed and time.monotonic() - self._failed[0] < LOAD_RETRY_SECONDS:
                raise self._failed[1]
            try:
                self._inner = OnnxEmbedder(*self._args)
            except Exception as exc:
                self._failed = (time.monotonic(), exc)
                raise
        return self._inner.embed(texts)


def make_embedder(settings: dict, models_dir: Path | None = None) -> tuple[Embedder | None, str | None]:
    """按配置创建嵌入器；不可用时返回 (None, 原因)，调用方退化为纯关键词检索。"""
    import importlib.util

    backend = settings.get("backend") or "auto"
    model = settings.get("model") or ""
    if backend == "none":
        return None, "配置为不使用嵌入"
    if backend == "ollama":
        if embed_url(settings.get("base_url") or "http://localhost:11434") is None:
            return None, _REMOTE_REFUSED
        return OllamaEmbedder(model or "bge-m3", settings.get("base_url") or ""), None
    if backend == "openai":
        if not settings.get("base_url"):
            return None, "openai 后端需要配置 embedding.base_url"
        if embed_url(settings["base_url"]) is None:
            return None, _REMOTE_REFUSED
        return OpenAIEmbedder(model, settings["base_url"]), None
    if importlib.util.find_spec("fastembed") is None:
        return None, "未安装 fastembed（uv tool install 'pmem[embed]' 可启用语义检索）"
    return LazyOnnxEmbedder(model or DEFAULT_ONNX_MODEL, settings.get("model_path") or "", models_dir), None
