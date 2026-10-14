from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

import numpy as np

from pmem.index.tokenize import tokenize

DEFAULT_ONNX_MODEL = "BAAI/bge-small-zh-v1.5"


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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class OllamaEmbedder(Embedder):
    def __init__(self, model: str, base_url: str = ""):
        self.model = model
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.id = f"ollama:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        result = _post_json(f"{self.base_url}/api/embed", {"model": self.model, "input": texts})
        return _normalise(np.array(result["embeddings"], dtype=np.float32))


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.id = f"openai:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        key = os.environ.get("PMEM_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        result = _post_json(f"{self.base_url}/embeddings", {"model": self.model, "input": texts}, headers)
        rows = sorted(result["data"], key=lambda item: item["index"])
        return _normalise(np.array([row["embedding"] for row in rows], dtype=np.float32))


def make_embedder(settings: dict, cache_dir: Path | None = None) -> tuple[Embedder | None, str | None]:
    """按配置创建嵌入器；不可用时返回 (None, 原因)，调用方退化为纯关键词检索。"""
    backend = settings.get("backend") or "auto"
    model = settings.get("model") or ""
    try:
        if backend == "none":
            return None, "配置为不使用嵌入"
        if backend == "ollama":
            return OllamaEmbedder(model or "bge-m3", settings.get("base_url") or ""), None
        if backend == "openai":
            if not settings.get("base_url"):
                return None, "openai 后端需要配置 embedding.base_url"
            return OpenAIEmbedder(model, settings["base_url"]), None
        model_dir = cache_dir / "models" if cache_dir else None
        return OnnxEmbedder(model or DEFAULT_ONNX_MODEL, settings.get("model_path") or "", model_dir), None
    except ImportError:
        return None, "未安装 fastembed（uv tool install 'pmem[embed]' 可启用语义检索）"
    except Exception as exc:  # noqa: BLE001
        return None, f"嵌入后端初始化失败：{exc}"
