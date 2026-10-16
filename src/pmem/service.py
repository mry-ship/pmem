from __future__ import annotations

import difflib
import functools
import time
from collections import Counter
from datetime import date
from pathlib import Path

from pmem.core.config import Config, user_cache_base
from pmem.core.entry import KINDS, Entry
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints, entity_hint
from pmem.core.registry import ModuleRegistry, RegistryError, ResolvedModule
from pmem.core.secrets import find_secrets
from pmem.core.textfmt import format_content
from pmem.index.embedder import make_embedder
from pmem.index.graph import MemoryGraph, preview
from pmem.index.store import MemoryIndex, SearchResult
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
ANCHOR_HINT = (
    "anchors 只写了文件：该文件以后任何改动都会让这条记忆标为“需核实”。能定位到函数时写成 路径#函数名"
    "（如 src/Reward.cs#Claim），只有这个函数改了才需要核实。"
)
HINTS_FOOTER = "以上只是提示，已写入；如需修改，带上 draft_id 再写一次即可覆盖。"
WRITABLE_STATUSES = ("active", "seed", "draft")
# 动作 → (允许的原状态, 新状态)；记忆文件写入后只有这些状态变更由负责人通过命令行发起。
# restore 回到归档前的状态，没记录时才用 active
STATUS_ACTIONS = {
    "archive": (("active", "seed", "draft"), "archived"),
    "restore": (("archived",), "active"),
    "accept": (("seed",), "active"),
    "reject": (("seed",), "archived"),
}


def _fail(message: str, **extra) -> dict:
    return {"ok": False, "error": message, **extra}


def _returns_errors(method):
    """模块名无法解析、modules.yaml 有误、写文件失败时返回 {"ok": False, "error": ...}，不抛给调用方。"""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (RegistryError, StorageError) as exc:
            return _fail(str(exc))

    return wrapper


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
    """MCP 工具与命令行背后的业务规则，两边共用。"""

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
        except ValueError as exc:  # 含 RegistryError
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
            match = self.registry.module_for_path(self._relative(path))
            if match is not None:
                module_id = match.module_id
                response["resolved_from"] = "path"
            elif not module:
                if not query:
                    return {"ok": True, "module": None, "items": [], "hint": "该路径未登记到任何模块；可带 query 全局检索"}
                response["hint"] = "该路径未登记到任何模块，已改为全局检索"
        if module and module_id is None:
            module_id = self._module_id(module)
        if module_id is None and not query:
            return _fail("请提供 module、path 或 query 其中之一")
        if module_id is not None and module_id not in self.registry.modules \
                and module_id not in self.index.module_stats():
            return {"ok": True, "module": module_id, "module_exists": False, "items": [],
                    "similar_modules": self._similar_modules(module_id)}

        entity_id = self.registry.resolve_entity(module_id or "", entity) if entity else None
        result = self._index_search(
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
        if any(i.get("stale") for i in result.items):
            response["verify_hint"] = VERIFY_HINT
        if module_id and not as_of:
            related = self.graph_model().related(module_id, entity_id, limit=MAX_RELATED)
            if related:
                response["related"] = [f"{r['module']}（{r['via']}）" for r in related]
        if result.fallback:
            response["fallback"] = result.fallback
        if result.degraded and (self.index.embedder_problem or self.index.embedder):
            response["degraded"] = result.degraded
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
        status: str | None = None,
    ) -> dict:
        response = self._record(module, entity, kind, content, supersedes, anchors, draft_id,
                                source_conversation, aliases, status)
        if not response.get("ok"):
            self._log("record_rejected", conv=source_conversation, module=module, entity=entity or None,
                      error=str(response.get("error") or "")[:200])
        return response

    @_returns_errors
    def _record(self, module, entity, kind, content, supersedes, anchors, draft_id, source_conversation, aliases,
                status) -> dict:
        resolved = self.registry.resolve_module(module)
        target = self.registry.modules.get(resolved.id)
        if target is not None and target.deprecated:
            return _fail(f"模块 {resolved.id} 已废弃（只读），不再接受新记忆；仍在维护的话先运行 "
                         f"pmem migrate deprecate {resolved.id} --undo --apply")
        if status and status not in WRITABLE_STATUSES:
            return _fail(f"status 只能是 {' / '.join(WRITABLE_STATUSES)}，当前为 {status!r}")
        content = (content or "").strip()
        problem = self._invalid_content(kind, content)
        if problem:
            return _fail(problem)
        entity_id = self.registry.resolve_entity(resolved.id, entity or "")
        if not entity_id:
            return _fail("entity 不能为空，用于区分模块内的议题，如 Reward、Config")

        # 替代自己的草稿说明要新建一条（草稿已提交时只能这样）；闸门可能按同议题自动注入了这个 draft_id
        if draft_id and draft_id in (supersedes or []):
            draft_id = None
        # 覆盖草稿时没传（None）的列表沿用原值，传空列表才清空；否则替代关系丢失，旧记忆会悄悄恢复现行
        old = self.index.find(draft_id) if draft_id else None
        if old is not None and old.status == "archived":
            return _fail(f"记忆 {draft_id} 已归档，不能覆盖；要接着用就先 pmem archive {draft_id} --restore，"
                         f"要写新结论就新建一条并在 supersedes 中写 {draft_id}")
        if old is not None:
            supersedes = old.supersedes if supersedes is None else supersedes
            anchors = old.anchors if anchors is None else anchors
            aliases = old.aliases if aliases is None else aliases
            if status is None and old.status in WRITABLE_STATUSES:
                status = old.status

        today = date.today().isoformat()
        supersedes = list(dict.fromkeys(s for s in supersedes or [] if s))
        replaced = [old for s in supersedes if (old := self.index.find(s)) is not None]
        aliases = _clean_aliases(aliases)
        hints = self._write_hints(resolved.id, entity_id, content, aliases, merging=len(replaced) >= 2)
        if anchors and not any("#" in a for a in anchors):
            hints.append(ANCHOR_HINT)
        # 替代旧记忆（含合并零碎记忆）不增加条数，不受每日上限约束
        if not draft_id and not replaced:
            over_cap = self._daily_cap_error(resolved.id, entity_id, today)
            if over_cap:
                return over_cap

        replaced_ids = [old.id for old in replaced]
        warnings = [f"supersedes 中的 {s} 不存在，已忽略对它的替代关系" for s in supersedes if s not in replaced_ids]
        if not anchors and replaced:
            anchors = list(dict.fromkeys(a for old in replaced for a in old.anchors))[:MAX_INHERITED_ANCHORS]
        entry = Entry(
            id=new_ulid(),
            module=resolved.id,
            entity=entity_id,
            kind=kind,
            content=format_content(content),
            note_date=today,
            author=self.vcs.current_user(),
            revision=self.vcs.revision(),
            status=status or str(self.config.get("write.default_status")),
            supersedes=replaced_ids,
            anchors=[a.replace("\\", "/") for a in anchors or []],
            source_conversation=source_conversation or None,
            aliases=aliases,
        )
        written = self.storage.write(entry, draft_id=draft_id or None)
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
        flags, module_warnings = self._module_notes(resolved)
        response.update(flags)
        warnings += module_warnings
        if warnings:
            response["warnings"] = warnings
        similar = self._similar_memories(written.entry)
        if similar:
            response["similar"] = similar
            hints.append(SIMILAR_HINT)
        if hints:
            response["hints"] = hints + [HINTS_FOOTER]
        self._refresh_wiki(response)
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

    def _invalid_content(self, kind: str, content: str) -> str | None:
        if kind not in KINDS:
            return f"kind 必须是 {' / '.join(KINDS)} 之一"
        low, high = int(self.config.get("write.content_min")), int(self.config.get("write.content_max"))
        if not low <= len(content) <= high:
            return f"正文长度需在 {low}–{high} 字之间，当前 {len(content)} 字"
        hits = find_secrets(content, self.config.get("write.secret_patterns") or [])
        if hits:
            return "正文疑似包含敏感信息，已拒绝写入：" + "；".join(hits)
        return None

    def _write_hints(self, module_id: str, entity_id: str, content: str, aliases: list[str], merging: bool) -> list[str]:
        """只提示、不拦截的写作建议。合并多条零碎记忆时篇长只受硬上限约束。"""
        limit_key = "write.content_max" if merging else "write.recommend_max"
        hints = content_hints(content, int(self.config.get(limit_key)))
        if not self.registry.is_global_entity(entity_id):
            new_entity = entity_hint(entity_id, self._known_entities(module_id))
            if new_entity:
                hints.append(new_entity)
        if not aliases:
            hints.append(ALIASES_HINT)
        return hints

    def _known_entities(self, module_id: str) -> list[str]:
        module = self.registry.modules.get(module_id) or self.registry.candidates.get(module_id)
        declared = [*module.entities, *module.components, *module.variants] if module else []
        used = [e.entity for e in self.index.entries() if e.module == module_id]
        return list(dict.fromkeys([*declared, *used]))

    def _daily_cap_error(self, module_id: str, entity_id: str, today: str) -> dict | None:
        same_day = [
            e.id for e in self.index.entries()
            if e.module == module_id and e.entity.lower() == entity_id.lower() and e.note_date == today
        ]
        cap = int(self.config.get("write.max_per_day_per_entity"))
        if len(same_day) < cap:
            return None
        return _fail(
            f"{module_id}/{entity_id} 今天已有 {len(same_day)} 条记忆，达到上限 {cap}；"
            "请把新结论合并进已有的一条（带 draft_id 覆盖自己未提交的那条），或用 supersedes 替代旧结论",
            existing_ids=same_day,
        )

    def _module_notes(self, resolved: ResolvedModule) -> tuple[dict, list[str]]:
        """写到别名、候选模块或未登记模块时，附在返回里的标记与提醒。"""
        flags: dict = {}
        warnings: list[str] = []
        if resolved.redirected_from:
            warnings.append(f"{resolved.redirected_from} 已并入 {resolved.id}")
        if resolved.candidate:
            flags["candidate_module"] = True
            warnings.append(f"{resolved.id} 是冷候选模块，已有记忆后建议负责人在 modules.yaml 中把它转为正式模块")
        elif not resolved.known:
            flags["new_module"] = True
            flags["similar_modules"] = [m for m in self._similar_modules(resolved.id) if m != resolved.id]
            warnings.append(f"{resolved.id} 尚未登记在 modules.yaml；如是笔误请改用相近模块")
        return flags, warnings

    def _similar_memories(self, entry: Entry) -> list[dict]:
        """同一议题下与新记忆最相近的有效记忆，交给写入的 Agent 判断是重复、推翻还是无关。

        只看同一实体：跨议题时相关度分不清真假（见 Ranking 排除项），每次都附两条无关记忆只会成为噪音。
        同一议题下条数很少，关键词就够；不加载语义模型，命令行写入因此快约 1 秒。
        """
        skip = {entry.id, *entry.supersedes}
        result = self._index_search(
            module=entry.module, entity=entry.entity, query=" ".join([entry.content, *entry.aliases]),
            limit=MAX_SIMILAR + len(skip), max_per_batch=MAX_LIMIT, verify=False, semantic=False,
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
        self._log("confirm", conv=source_conversation, ids=confirmed)
        response: dict = {"ok": bool(confirmed) or not missing, "confirmed": confirmed, "verified": today}
        if missing:
            response["missing"] = missing
        if confirmed:
            self.index.refresh(force=True)
            self._refresh_wiki(response)
        return response

    # ---- archive / seed ----

    def change_status(self, ids: list[str], action: str) -> dict:
        """归档、恢复、种子转正或退回。只改 YAML 头的状态，正文与替代关系不变。
        归档时记下日期和原状态：按日期回看时那天之后才归档的仍算有效，恢复时回到原状态。"""
        allowed, target = STATUS_ACTIONS[action]
        today = date.today().isoformat()
        changed, missing, skipped = [], [], []
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            entry = self.storage.read(path)
            if entry.status not in allowed:
                skipped.append({"id": entry_id, "status": entry.status})
                continue
            if target == "archived":
                entry.archived_on, entry.archived_from = today, entry.status
                entry.status = target
            else:
                entry.status = (entry.archived_from or target) if action == "restore" else target
                entry.archived_on = entry.archived_from = None
            path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
            changed.append(entry_id)
        self._log("status", action=action, ids=changed)
        response: dict = {"ok": bool(changed) or not (missing or skipped), "action": action, "status": target,
                          "changed": changed}
        if missing:
            response["missing"] = missing
        if skipped:
            response["skipped"] = skipped
        if changed:
            self.index.refresh(force=True)
            self._refresh_wiki(response)
        return response

    @_returns_errors
    def seeds(self, module: str | None = None) -> dict:
        """待确认的种子记忆，按模块、议题排列。"""
        module = self._module_id(module) if module else None
        rows = [
            {"id": e.id, "module": e.module, "entity": e.entity, "kind": e.kind, "date": e.note_date,
             "author": e.author, "preview": preview(e.content)}
            for e in sorted(self.index.visible(), key=lambda e: (e.module, e.entity.lower(), e.id))
            if e.status == "seed" and (module is None or e.module == module)
        ]
        return {"ok": True, "module": module, "seeds": rows}

    def _refresh_wiki(self, response: dict) -> None:
        """记忆变了就重新生成 Wiki（wiki.auto）；生成失败不影响写入本身，只附一条提醒。"""
        if not self.config.get("wiki.auto"):
            return
        from pmem.generate.wiki import write_wiki

        try:
            write_wiki(self, self.root / str(self.config.get("wiki.dir")))
        except Exception as exc:  # noqa: BLE001
            response.setdefault("warnings", []).append(f"Wiki 重新生成失败（记忆已写入）：{exc}")

    # ---- memory_graph ----

    @_returns_errors
    def graph(self, module: str, entity: str | None = None) -> dict:
        module_id = self._module_id(module)
        model = self.graph_model()
        if not entity:
            topics = model.topics(module_id)
            response = {"ok": True, "module": module_id, "topics": topics, "related": model.related(module_id)}
            return self._mark_stale(response, [row for t in topics for row in t["latest"]])
        entity_id = self.registry.resolve_entity(module_id, entity)
        timeline = model.timeline(module_id, entity_id)
        if not timeline:
            return _fail(f"{module_id}/{entity_id} 下没有记忆",
                         entities=[t["entity"] for t in model.topics(module_id)][:20])
        response = {"ok": True, "module": module_id, "entity": entity_id, "timeline": timeline,
                    "related": model.related(module_id, entity_id)}
        return self._mark_stale(response, [row for row in timeline if "superseded_by" not in row])

    def _mark_stale(self, response: dict, rows: list[dict]) -> dict:
        """给现行记忆的行标上 stale/check，与检索结果同一口径。"""
        entries = [e for e in (self.index.find(row["id"]) for row in rows) if e is not None]
        problems = self.index.check_anchors(entries)
        for row in rows:
            if row["id"] in problems:
                row["stale"] = True
                row["check"] = problems[row["id"]]
        if problems:
            response["verify_hint"] = VERIFY_HINT
        return response

    # ---- terms ----

    @_returns_errors
    def terms(self, module: str | None = None, top: int = 300, min_count: int = 2) -> dict:
        """有效记忆里的高频词（按出现在几条记忆里计），供 Agent 找出同一件事的不同叫法。"""
        module = self._module_id(module) if module else None
        docs: Counter = Counter()
        where: dict[str, Counter] = {}
        for entry in self.index.visible():
            if module and entry.module != module:
                continue
            words = {t for t in tokenize(f"{entry.content} {' '.join(entry.aliases)}")
                     if len(t) >= 2 and not t.isdigit() and not (t.isascii() and len(t) < 3)}
            for word in sorted(words):
                docs[word] += 1
                where.setdefault(word, Counter())[entry.module] += 1
        rows = [{"term": w, "memories": n, "modules": [m for m, _ in where[w].most_common(2)]}
                for w, n in docs.most_common() if n >= min_count][:top]
        return {"ok": True, "module": module, "synonyms": [list(g) for g in self.registry.synonyms], "terms": rows}

    # ---- list_modules ----

    @_returns_errors
    def list_modules(self, category: str | None = None) -> dict:
        registry = self.registry
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
            if module is not None and module.deprecated:
                row["deprecated"] = True
            rows.append(row)
        return {"ok": True, "categories": registry.categories, "modules": rows, "registered_empty": empty}

    # ---- compact ----

    def _topic_groups(self, module: str | None = None) -> dict[tuple[str, str], list[Entry]]:
        """按 (模块, 议题) 分组的有效记忆，组内从旧到新。"""
        groups: dict[tuple[str, str], list[Entry]] = {}
        for entry in sorted(self.index.visible(), key=lambda e: (e.note_date, e.id)):
            if module and entry.module.lower() != module.lower():
                continue
            groups.setdefault((entry.module, entry.entity.lower()), []).append(entry)
        return groups

    @_returns_errors
    def compact_groups(self, module: str | None = None, min_size: int = COMPACT_MIN_GROUP) -> dict:
        """同一模块同一议题积累了多条记忆的分组，按条数从多到少。"""
        module = self._module_id(module) if module else None
        rows = [
            {
                "module": module_id,
                "entity": items[-1].entity,
                "count": len(items),
                "chars": sum(len(e.content) for e in items),
                "first": items[0].note_date,
                "last": items[-1].note_date,
                "kinds": dict(Counter(e.kind for e in items)),
            }
            for (module_id, _), items in self._topic_groups(module).items()
            if len(items) >= min_size
        ]
        rows.sort(key=lambda r: (-r["count"], r["module"], r["entity"]))
        return {"ok": True, "min_size": min_size, "groups": rows, "memories": sum(r["count"] for r in rows)}

    @_returns_errors
    def compact_group(self, module: str, entity: str) -> dict:
        """一个议题下全部有效记忆的正文（从旧到新），供合并成一条。"""
        module_id = self._module_id(module)
        entity_id = self.registry.resolve_entity(module_id, entity)
        items = self._topic_groups(module_id).get((module_id, entity_id.lower()), [])
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
