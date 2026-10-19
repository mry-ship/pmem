"""服务的公共部分：配置、模块目录、索引、版本库等依赖的懒加载，错误返回的统一形状，以及几类操作都要用的小工具。"""
from __future__ import annotations

import difflib
import functools
from datetime import date
from pathlib import Path

from pmem.core.config import Config, user_cache_base
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.index.embedder import make_embedder
from pmem.index.graph import MemoryGraph
from pmem.index.store import MemoryIndex, SearchResult
from pmem.metrics.events import log_event
from pmem.storage.files import FilesStorage, StorageError
from pmem.vcs.detect import detect_vcs

MAX_LIMIT = 10
VERIFY_HINT = (
    "stale=true 的记忆写下（或上次核对）之后，关联代码又改过或已不存在，见各条 check。"
    "依赖它之前先打开关联代码核对：仍然成立就调用 confirm_memory(ids=[...]) 刷新核对日期；"
    "已不成立就写一条 correction，supersedes 填它的 id。"
)


def fail(message: str, code: str | None = None, **extra) -> dict:
    """code 是稳定的错误类别（统计按它归类），message 是给人看的提示。"""
    return {"ok": False, "error": message, **({"code": code} if code else {}), **extra}


def returns_errors(method):
    """模块名无法解析、modules.yaml 有误、写文件失败时返回 {"ok": False, "error": ...}，不抛给调用方。"""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (RegistryError, StorageError) as exc:
            return fail(str(exc), exc.code)

    return wrapper


def valid_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw).strip()).isoformat()
    except ValueError as exc:
        raise ValueError(f"as_of 需要 YYYY-MM-DD 格式的日期，当前为 {raw!r}") from exc


class ServiceBase:
    def __init__(self, root: str | Path, source: str = "cli"):
        self.config = Config.load(root)
        self.root = self.config.root
        self.source = source
        self.vcs = detect_vcs(self.root, self.config.get("vcs"))
        self._user: str | None = None
        self.storage = FilesStorage(self.root, self.vcs, bool(self.config.get("svn_auto_add")))
        self._registry: ModuleRegistry | None = None
        self._registry_stamp: tuple[int, int] | None = None
        self._index: MemoryIndex | None = None
        self._graph: tuple[tuple, MemoryGraph] | None = None

    # ---- 依赖的懒加载 ----

    @property
    def registry(self) -> ModuleRegistry:
        path = self.config.modules_path
        stamp = (path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else None
        if self._registry is None or stamp != self._registry_stamp:
            self._registry = ModuleRegistry.load(path) if path.exists() else ModuleRegistry({})
            self._registry_stamp = stamp
        return self._registry

    @property
    def index(self) -> MemoryIndex:
        if self._index is None:
            settings = self.config.get("embedding") or {}
            embedder, problem = make_embedder(settings, user_cache_base() / "models")
            if settings.get("backend") in ("auto", "none"):
                problem = None
            self._index = MemoryIndex(self.storage, self.config.cache_dir, embedder, problem)
        return self._index

    def close(self) -> None:
        if self._index is not None:
            self._index.close()

    def graph_model(self) -> MemoryGraph:
        registry = self.registry
        entries = self.index.entries()
        key = (self.index.version, self._registry_stamp)
        if self._graph is None or self._graph[0] != key:
            self._graph = (key, MemoryGraph(entries, registry))
        return self._graph[1]

    @property
    def user(self) -> str:
        if self._user is None:
            self._user = self.vcs.current_user()
        return self._user

    # ---- 几类操作共用 ----

    def _log(self, event_type: str, **fields) -> None:
        log_event(self.config.cache_dir, event_type, source=self.source, user=self.user, **fields)

    def _module_id(self, name: str) -> str:
        return self.registry.resolve_module(name).id

    def _similar_modules(self, name: str) -> list[str]:
        known = set(self.registry.modules) | set(self.index.module_stats())
        lowered = {k.lower(): k for k in known}
        hits = difflib.get_close_matches(name.lower(), list(lowered), n=3, cutoff=0.6)
        return [lowered[h] for h in hits]

    def _index_search(self, **kwargs) -> SearchResult:
        self.index.synonyms = self.registry.synonyms
        return self.index.search(**kwargs)

    def _relative(self, path: str) -> str:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                return candidate.resolve().relative_to(self.root).as_posix()
            except ValueError:
                return candidate.as_posix()
        return path

    def _refresh_wiki(self, response: dict) -> None:
        """记忆变了就重新生成 Wiki（wiki.auto）；生成失败不影响写入本身，只附一条提醒。"""
        if not self.config.get("wiki.auto"):
            return
        from pmem.generate.wiki import write_wiki

        try:
            write_wiki(self, self.root / str(self.config.get("wiki.dir")))
        except Exception as exc:  # noqa: BLE001
            response.setdefault("warnings", []).append(f"Wiki 重新生成失败（记忆已写入）：{exc}")
