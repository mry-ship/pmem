from __future__ import annotations

import difflib
from datetime import date
from pathlib import Path

from pmem.core.config import Config
from pmem.core.entry import KINDS, Entry
from pmem.core.ids import new_ulid
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.core.secrets import find_secrets
from pmem.index.embedder import make_embedder
from pmem.index.store import MemoryIndex
from pmem.storage.files import FilesStorage, StorageError
from pmem.vcs.detect import detect_vcs

MAX_LIMIT = 10


def _fail(message: str, **extra) -> dict:
    return {"ok": False, "error": message, **extra}


class MemoryService:
    """三个工具背后的业务规则；MCP 与 CLI 共用。"""

    def __init__(self, root: str | Path):
        self.config = Config.load(root)
        self.root = self.config.root
        self.vcs = detect_vcs(self.root, self.config.get("vcs"))
        self.storage = FilesStorage(self.root, self.vcs, bool(self.config.get("svn_auto_add")))
        self._registry: ModuleRegistry | None = None
        self._registry_stamp: tuple[int, int] | None = None
        self._index: MemoryIndex | None = None

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
            embedder, problem = make_embedder(settings, self.config.cache_dir)
            if settings.get("backend") in ("auto", "none"):
                problem = None
            self._index = MemoryIndex(self.storage, self.config.cache_dir, embedder, problem)
        return self._index

    def close(self) -> None:
        if self._index is not None:
            self._index.close()

    def _similar(self, name: str) -> list[str]:
        known = set(self.registry.modules) | set(self.index.module_stats())
        lowered = {k.lower(): k for k in known}
        hits = difflib.get_close_matches(name.lower(), list(lowered), n=3, cutoff=0.6)
        return [lowered[h] for h in hits]

    # ---- search_memory ----

    def search(
        self,
        module: str | None = None,
        path: str | None = None,
        entity: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> dict:
        limit = max(1, min(int(limit or self.config.get("search.limit")), MAX_LIMIT))
        response: dict = {"ok": True}
        module_id: str | None = None
        if path:
            try:
                match = self.registry.module_for_path(self._relative(path))
            except RegistryError as exc:
                return _fail(str(exc))
            if match is None and not module:
                if not query:
                    return {"ok": True, "module": None, "items": [], "hint": "该路径未登记到任何模块；可带 query 全局检索"}
                response["hint"] = "该路径未登记到任何模块，已改为全局检索"
            elif match is not None:
                module_id = match.module_id
                response["resolved_from"] = "path"
        if module and module_id is None:
            try:
                resolved = self.registry.resolve_module(module)
            except RegistryError as exc:
                return _fail(str(exc))
            module_id = resolved.id
        if module_id is None and not query:
            return _fail("请提供 module、path 或 query 其中之一")

        if module_id is not None:
            exists = module_id in self.registry.modules or module_id in self.index.module_stats()
            if not exists:
                return {"ok": True, "module": module_id, "module_exists": False, "items": [],
                        "similar_modules": self._similar(module_id)}

        entity_id = self.registry.resolve_entity(module_id or "", entity) if entity else None
        result = self.index.search(
            module=module_id,
            entity=entity_id,
            query=query,
            limit=limit,
            max_per_batch=int(self.config.get("search.max_per_batch")),
            half_life_days=float(self.config.get("search.recency_half_life_days")),
        )
        response.update({"module": module_id, "items": result.items})
        if result.fallback:
            response["fallback"] = result.fallback
        degraded = result.degraded if self.index.embedder_problem or self.index.embedder else None
        if degraded:
            response["degraded"] = degraded
        warnings = result.warnings + ([self.index.embedder_problem] if self.index.embedder_problem else [])
        if warnings:
            response["warnings"] = warnings
        return response

    def _relative(self, path: str) -> str:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                return candidate.resolve().relative_to(self.root).as_posix()
            except ValueError:
                return candidate.as_posix()
        return path

    # ---- record_memory ----

    def record(
        self,
        module: str,
        entity: str,
        kind: str,
        content: str,
        supersedes: list[str] | None = None,
        anchors: list[str] | None = None,
        draft_id: str | None = None,
        source_conversation: str | None = None,
    ) -> dict:
        try:
            resolved = self.registry.resolve_module(module)
        except RegistryError as exc:
            return _fail(str(exc))
        if kind not in KINDS:
            return _fail(f"kind 必须是 {' / '.join(KINDS)} 之一")
        content = (content or "").strip()
        low, high = int(self.config.get("write.content_min")), int(self.config.get("write.content_max"))
        if not low <= len(content) <= high:
            return _fail(f"正文长度需在 {low}–{high} 字之间，当前 {len(content)} 字")
        hits = find_secrets(content, self.config.get("write.secret_patterns") or [])
        if hits:
            return _fail("正文疑似包含敏感信息，已拒绝写入：" + "；".join(hits))
        entity_id = self.registry.resolve_entity(resolved.id, entity or "")
        if not entity_id:
            return _fail("entity 不能为空，用于区分模块内的议题，如 Reward、Config")

        today = date.today().isoformat()
        author = self.vcs.current_user()
        if not draft_id:
            same_day = [
                e.id
                for e in self.index.entries()
                if e.module == resolved.id and e.entity.lower() == entity_id.lower() and e.note_date == today
            ]
            cap = int(self.config.get("write.max_per_day_per_entity"))
            if len(same_day) >= cap:
                return _fail(
                    f"{resolved.id}/{entity_id} 今天已有 {len(same_day)} 条记忆，达到上限 {cap}；"
                    "请把新结论合并进已有的一条（带 draft_id 覆盖自己未提交的那条），或用 supersedes 替代旧结论",
                    existing_ids=same_day,
                )

        warnings: list[str] = []
        supersedes = [s for s in (supersedes or []) if s]
        for old_id in supersedes:
            if self.index.find(old_id) is None:
                warnings.append(f"supersedes 中的 {old_id} 不存在，已忽略对它的替代关系")
        entry = Entry(
            id=new_ulid(),
            module=resolved.id,
            entity=entity_id,
            kind=kind,
            content=content,
            note_date=today,
            author=author,
            revision=self.vcs.revision(),
            status=str(self.config.get("write.default_status")),
            supersedes=[s for s in supersedes if self.index.find(s) is not None],
            anchors=[a.replace("\\", "/") for a in anchors or []],
            source_conversation=source_conversation or None,
        )
        try:
            written = self.storage.write(entry, draft_id=draft_id or None)
        except StorageError as exc:
            return _fail(str(exc))
        self.index.refresh(force=True)

        response = {
            "ok": True,
            "id": written.entry.id,
            "module": resolved.id,
            "entity": entity_id,
            "path": written.path.relative_to(self.root).as_posix(),
            "overwritten": written.overwritten,
            "draft_id": written.entry.id,
        }
        if resolved.redirected_from:
            warnings.append(f"{resolved.redirected_from} 已并入 {resolved.id}")
        if resolved.candidate:
            response["candidate_module"] = True
            warnings.append(f"{resolved.id} 是冷候选模块，已有记忆后建议负责人在 modules.yaml 中把它转为正式模块")
        elif not resolved.known:
            response["new_module"] = True
            response["similar_modules"] = [m for m in self._similar(resolved.id) if m != resolved.id]
            warnings.append(f"{resolved.id} 尚未登记在 modules.yaml；如是笔误请改用相近模块")
        if warnings:
            response["warnings"] = warnings
        return response

    # ---- list_modules ----

    def list_modules(self, category: str | None = None) -> dict:
        stats = self.index.module_stats()
        registry = self.registry
        rows, empty = [], []
        for module_id in sorted(set(registry.modules) | set(stats)):
            if category and not module_id.lower().startswith(category.lower() + "."):
                continue
            module = registry.modules.get(module_id)
            if module is not None and module.merged_into:
                continue
            stat = stats.get(module_id)
            if stat is None:
                empty.append(module_id)
                continue
            row = {"module": module_id, "count": stat["count"], "entities": stat["entities"],
                   "registered": module is not None}
            if module is not None and module.aliases:
                row["aliases"] = module.aliases
            rows.append(row)
        return {"ok": True, "categories": registry.categories, "modules": rows, "registered_empty": empty}
