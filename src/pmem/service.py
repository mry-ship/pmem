from __future__ import annotations

import difflib
import time
from collections import Counter
from datetime import date
from pathlib import Path

from pmem.core.config import Config, user_cache_base
from pmem.core.entry import KINDS, Entry
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints, entity_hint
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.core.secrets import find_secrets
from pmem.index.embedder import make_embedder
from pmem.index.graph import MemoryGraph, preview
from pmem.index.store import VISIBLE_STATUSES, MemoryIndex
from pmem.index.tokenize import tokenize
from pmem.metrics.events import log_event
from pmem.storage.files import FilesStorage, StorageError
from pmem.vcs.detect import detect_vcs

MAX_LIMIT = 10
MAX_INHERITED_ANCHORS = 10
COMPACT_MIN_GROUP = 5
MAX_RELATED = 3
MAX_SIMILAR = 2
MAX_ALIASES = 10
MAX_ALIAS_CHARS = 30
VERIFY_HINT = (
    "stale=true 的记忆写下（或上次核对）之后，关联代码又改过或已不存在，见各条 check。"
    "依赖它之前先打开关联代码核对：仍然成立就调用 confirm_memory(ids=[...]) 刷新核对日期；"
    "已不成立就写一条 correction，supersedes 填它的 id。"
)
SIMILAR_HINT = (
    "similar 是同模块最相近的已有记忆：新结论与其中某条重复或推翻了它，就带 draft_id 重写并在 supersedes 填那条的 id；"
    "无关则忽略。"
)
ALIASES_HINT = "没填 aliases：把现象和关键术语的其他常用叫法（如 闪退/崩溃/crash）写进 aliases，换个说法也能搜到。"


def _fail(message: str, **extra) -> dict:
    return {"ok": False, "error": message, **extra}


def _valid_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw).strip()).isoformat()
    except ValueError as exc:
        raise ValueError(f"as_of 需要 YYYY-MM-DD 格式的日期，当前为 {raw!r}") from exc


def _clean_aliases(raw: list[str] | None) -> list[str]:
    seen: list[str] = []
    for alias in raw or []:
        text = str(alias).strip()
        if text and len(text) <= MAX_ALIAS_CHARS and text.lower() not in {s.lower() for s in seen}:
            seen.append(text)
    return seen[:MAX_ALIASES]


class MemoryService:
    """三个工具背后的业务规则；MCP 与 CLI 共用。"""

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

    def _log(self, event_type: str, **fields) -> None:
        log_event(self.config.cache_dir, event_type, source=self.source, user=self.user, **fields)

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
        source_conversation: str | None = None,
        as_of: str | None = None,
    ) -> dict:
        started = time.perf_counter()
        try:
            response = self._search(module, path, entity, query, limit, _valid_date(as_of))
        except (RegistryError, ValueError) as exc:
            response = _fail(str(exc))
        items = response.get("items") or []
        self._log(
            "search",
            conv=source_conversation,
            ok=response.get("ok"),
            module=response.get("module"),
            entity=entity or None,
            query=(query or None) and query[:200],
            ids=[i["id"] for i in items],
            kinds=[i["kind"] for i in items],
            authors=[i.get("author") for i in items],
            fallback=response.get("fallback"),
            ms=round((time.perf_counter() - started) * 1000),
        )
        return response

    def _search(self, module, path, entity, query, limit, as_of=None) -> dict:
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
        self.index.synonyms = self.registry.synonyms
        result = self.index.search(
            module=module_id,
            entity=entity_id,
            query=query,
            limit=limit,
            max_per_batch=int(self.config.get("search.max_per_batch")),
            half_life_days=float(self.config.get("search.recency_half_life_days")),
            as_of=as_of,
        )
        response.update({"module": module_id, "items": result.items})
        if as_of:
            response["as_of"] = as_of
        if result.expanded:
            response["expanded"] = result.expanded
        stale = [i["id"] for i in result.items if i.get("stale")]
        if stale:
            response["verify_hint"] = VERIFY_HINT
        if module_id and not as_of:
            related = self.graph_model().related(module_id, entity_id, limit=MAX_RELATED)
            if related:
                response["related"] = [f"{r['module']}（{r['via']}）" for r in related]
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
        aliases: list[str] | None = None,
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
        module_def = self.registry.modules.get(resolved.id) or self.registry.candidates.get(resolved.id)
        declared = [*module_def.entities, *module_def.components, *module_def.variants] if module_def else []
        known_entities = list(dict.fromkeys(
            [*declared, *(e.entity for e in self.index.entries() if e.module == resolved.id)]
        ))
        supersedes = list(dict.fromkeys(s for s in supersedes or [] if s))
        replaced = [old for s in supersedes if (old := self.index.find(s)) is not None]
        # 合并多条零碎记忆时只受硬上限约束
        recommend_max = high if len(replaced) >= 2 else int(self.config.get("write.recommend_max"))
        hints = content_hints(content, recommend_max)
        if not self.registry.is_global_entity(entity_id) and (new_entity := entity_hint(entity_id, known_entities)):
            hints.append(new_entity)
        aliases = _clean_aliases(aliases)
        if not aliases:
            hints.append(ALIASES_HINT)
        # 替代旧记忆（含合并零碎记忆）不增加条数，不受每日上限约束
        if not draft_id and not replaced:
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

        warnings = [f"supersedes 中的 {s} 不存在，已忽略对它的替代关系"
                    for s in supersedes if s not in {old.id for old in replaced}]
        if not anchors and replaced:
            anchors = list(dict.fromkeys(a for old in replaced for a in old.anchors))[:MAX_INHERITED_ANCHORS]
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
            supersedes=[old.id for old in replaced],
            anchors=[a.replace("\\", "/") for a in anchors or []],
            source_conversation=source_conversation or None,
            aliases=aliases,
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
        similar = self._similar_memories(written.entry)
        if similar:
            response["similar"] = similar
            hints.append(SIMILAR_HINT)
        if hints:
            response["hints"] = hints + ["以上只是提示，已写入；如需修改，带上 draft_id 再写一次即可覆盖。"]
        self._log(
            "record",
            conv=source_conversation,
            id=written.entry.id,
            module=resolved.id,
            entity=entity_id,
            kind=kind,
            overwritten=written.overwritten,
            supersedes=entry.supersedes or None,
        )
        return response

    def _similar_memories(self, entry: Entry) -> list[dict]:
        """同一议题下与新记忆最相近的有效记忆，交给写入的 Agent 判断是重复、推翻还是无关。

        只看同一实体：跨议题时相关度分不清真假（见 Ranking 排除项），每次都附两条无关记忆只会成为噪音。
        """
        skip = {entry.id, *entry.supersedes}
        self.index.synonyms = self.registry.synonyms
        result = self.index.search(
            module=entry.module, entity=entry.entity, query=" ".join([entry.content, *entry.aliases]),
            limit=MAX_SIMILAR + len(skip), max_per_batch=MAX_LIMIT, verify=False,
        )
        rows = [
            {"id": i["id"], "entity": i["entity"], "kind": i["kind"], "date": i["date"], "preview": preview(i["content"])}
            for i in result.items if i["id"] not in skip
        ]
        return rows[:MAX_SIMILAR]

    # ---- confirm_memory ----

    def confirm(self, ids: list[str], source_conversation: str | None = None) -> dict:
        """核对过关联代码、仍然成立的记忆：把核对日期记为今天，之后不再因更早的代码改动标为 stale。"""
        today = date.today().isoformat()
        confirmed, missing = [], []
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            entry = self.storage.read(path)
            entry.verified = today
            path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
            confirmed.append(entry_id)
        if confirmed:
            self.index.refresh(force=True)
        self._log("confirm", conv=source_conversation, ids=confirmed)
        response: dict = {"ok": bool(confirmed) or not missing, "confirmed": confirmed, "verified": today}
        if missing:
            response["missing"] = missing
        return response

    # ---- memory_graph ----

    def graph(self, module: str, entity: str | None = None) -> dict:
        try:
            module_id = self.registry.resolve_module(module).id
        except RegistryError as exc:
            return _fail(str(exc))
        model = self.graph_model()
        if entity:
            entity_id = self.registry.resolve_entity(module_id, entity)
            timeline = model.timeline(module_id, entity_id)
            if not timeline:
                return _fail(f"{module_id}/{entity_id} 下没有记忆",
                             entities=[t["entity"] for t in model.topics(module_id)][:20])
            return {"ok": True, "module": module_id, "entity": entity_id, "timeline": timeline,
                    "related": model.related(module_id, entity_id)}
        return {"ok": True, "module": module_id, "topics": model.topics(module_id),
                "related": model.related(module_id)}

    # ---- terms ----

    def terms(self, module: str | None = None, top: int = 300, min_count: int = 2) -> dict:
        """有效记忆里的高频词（按出现在几条记忆里计），供 Agent 找出同一件事的不同叫法。"""
        if module:
            try:
                module = self.registry.resolve_module(module).id
            except RegistryError as exc:
                return _fail(str(exc))
        docs: Counter = Counter()
        where: dict[str, Counter] = {}
        hidden = self.index.superseded()
        for entry in self.index.entries():
            if entry.status not in VISIBLE_STATUSES or entry.id in hidden or (module and entry.module != module):
                continue
            words = {t for t in tokenize(f"{entry.content} {' '.join(entry.aliases)}")
                     if len(t) >= 2 and not t.isdigit() and not (t.isascii() and len(t) < 3)}
            for word in words:
                docs[word] += 1
                where.setdefault(word, Counter())[entry.module] += 1
        known = [list(g) for g in self.registry.synonyms]
        rows = [{"term": w, "memories": n, "modules": [m for m, _ in where[w].most_common(2)]}
                for w, n in docs.most_common() if n >= min_count][:top]
        return {"ok": True, "module": module, "synonyms": known, "terms": rows}

    # ---- list_modules ----

    def list_modules(self, category: str | None = None) -> dict:
        try:
            registry = self.registry
        except RegistryError as exc:
            return _fail(str(exc))
        stats = self.index.module_stats()
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

    # ---- compact ----

    def _visible_groups(self, module: str | None = None) -> dict[tuple[str, str], list[Entry]]:
        hidden = self.index.superseded()
        groups: dict[tuple[str, str], list[Entry]] = {}
        for entry in sorted(self.index.entries(), key=lambda e: (e.note_date, e.id)):
            if entry.status not in VISIBLE_STATUSES or entry.id in hidden:
                continue
            if module and entry.module.lower() != module.lower():
                continue
            groups.setdefault((entry.module, entry.entity.lower()), []).append(entry)
        return groups

    def compact_groups(self, module: str | None = None, min_size: int = COMPACT_MIN_GROUP) -> dict:
        """同一模块同一议题积累了多条记忆的分组，按条数从多到少。"""
        if module:
            try:
                module = self.registry.resolve_module(module).id
            except RegistryError as exc:
                return _fail(str(exc))
        rows = []
        for (module_id, _), items in self._visible_groups(module).items():
            if len(items) < min_size:
                continue
            rows.append({
                "module": module_id,
                "entity": items[-1].entity,
                "count": len(items),
                "chars": sum(len(e.content) for e in items),
                "first": items[0].note_date,
                "last": items[-1].note_date,
                "kinds": dict(Counter(e.kind for e in items)),
            })
        rows.sort(key=lambda r: (-r["count"], r["module"], r["entity"]))
        return {"ok": True, "min_size": min_size, "groups": rows, "memories": sum(r["count"] for r in rows)}

    def compact_group(self, module: str, entity: str) -> dict:
        """一个议题下全部有效记忆的正文（从旧到新），供合并成一条。"""
        try:
            module_id = self.registry.resolve_module(module).id
        except RegistryError as exc:
            return _fail(str(exc))
        entity_id = self.registry.resolve_entity(module_id, entity)
        items = self._visible_groups(module_id).get((module_id, entity_id.lower()), [])
        if not items:
            return _fail(f"{module_id}/{entity_id} 下没有有效记忆")
        return {
            "ok": True,
            "module": module_id,
            "entity": items[-1].entity,
            "chars": sum(len(e.content) for e in items),
            "items": [
                {"id": e.id, "kind": e.kind, "date": e.note_date, "author": e.author,
                 "anchors": e.anchors, "content": e.content}
                for e in items
            ],
        }
