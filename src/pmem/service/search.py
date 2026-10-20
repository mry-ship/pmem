"""检索类操作：search_memory、memory_graph、list_modules。只读，不改记忆文件。"""
from __future__ import annotations

import time

from pmem.core import seen
from pmem.core.entry import auto_summary
from pmem.index.store import entry_row
from pmem.service.base import MAX_LIMIT, VERIFY_HINT, ServiceBase, fail, returns_errors, valid_date

MAX_RELATED = 3
SEEN_HINT = ("标 seen 的 {n} 条本对话已经返回过全文，这次只列标题；上下文里找不到原文时，"
             "带 full=true（命令行 --full）重查。")
FEATURES_HINT = ("features 是本模块已实现的功能（feature）和未实现的规划（plan），只列标题：功能里写的是用户要求、"
                 "必须保持的行为，改动会改变这些行为时先用 ids=[...]（命令行 --id）取全文核对，不要把它们当冗余代码改回去；"
                 "规划还没实现，不是现状。")
APPLIES_HINT = "带 applies 的记忆只在该前提下成立：先判断当前情况是否满足，不满足就不要套用。"
_KEPT_ON_COLLAPSE = ("module", "id", "entity", "kind", "date", "stale", "check", "status", "scope", "applies")


class SearchOps(ServiceBase):
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
        full: bool = False,
        ids: list[str] | None = None,
    ) -> dict:
        started = time.perf_counter()
        try:
            if ids:
                response, full = self._by_ids(ids), True
            else:
                response = self._search(module, path, entity, query, limit, valid_date(as_of))
        except ValueError as exc:  # 含 RegistryError
            response = fail(str(exc))
        conversation = source_conversation or self._claim_conversation(response)
        collapsed = self._collapse_seen(response, conversation, full) if response.get("ok") else []
        items = response.get("items") or []
        self._log(
            "search",
            conv=conversation,
            ok=response.get("ok"),
            module=response.get("module"),
            path=(path or None) and self._relative(path),
            entity=entity or None,
            query=(query or None) and query[:200],
            ids=[i["id"] for i in items],
            kinds=[i["kind"] for i in items],
            authors=[i.get("author") for i in items],
            fallback=response.get("fallback"),
            collapsed=collapsed or None,
            ms=round((time.perf_counter() - started) * 1000),
        )
        return response

    def _claim_conversation(self, response: dict) -> str | None:
        """终端里的 pmem search 不带对话 id，认领 Hook 执行前登记的那个对话。"""
        if self.source != "cli" or not response.get("ok"):
            return None
        return seen.claim_handoff(self.config.cache_dir, response.get("module"))

    def _collapse_seen(self, response: dict, conversation: str | None, full: bool) -> list[str]:
        """同一对话里已返回过全文的记忆只给标题，其余照常返回并记为已返回；返回被折叠的 id。"""
        items = response.get("items") or []
        if not conversation or not items:
            return []
        cache_dir = self.config.cache_dir
        shown = set() if full else seen.load(cache_dir, conversation)
        rows, collapsed, fresh = [], [], []
        for item in items:
            if item["id"] in shown:
                row = {k: item[k] for k in _KEPT_ON_COLLAPSE if k in item}
                row["summary"] = item.get("summary") or auto_summary(item.get("content") or "")
                row["seen"] = True
                rows.append(row)
                collapsed.append(item["id"])
            else:
                rows.append(item)
                fresh.append(item["id"])
        seen.add(cache_dir, conversation, fresh)
        response["items"] = rows
        if collapsed:
            response["seen_hint"] = SEEN_HINT.format(n=len(collapsed))
        return collapsed

    def _by_ids(self, ids: list[str]) -> dict:
        """按 id 取全文（功能记录、去重后的标题都可以这样展开）；被替代、归档的也给，并标出状态。"""
        wanted = list(dict.fromkeys(str(i).strip() for i in ids if str(i).strip()))[:MAX_LIMIT]
        entries = [e for e in (self.index.find(i) for i in wanted) if e is not None]
        problems = self.index.check_anchors(entries)
        modules = {e.module for e in entries}
        response: dict = {"ok": True, "module": next(iter(modules)) if len(modules) == 1 else None,
                          "items": [entry_row(e, problems.get(e.id), with_module=True) for e in entries]}
        missing = [i for i in wanted if i not in {e.id for e in entries}]
        if missing:
            response["missing"] = missing
        if problems:
            response["verify_hint"] = VERIFY_HINT
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
            return fail("请提供 module、path 或 query 其中之一")
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
            path=self._relative(path) if path else None,
            feature_limit=max(0, int(self.config.get("search.feature_limit", 3))),
        )
        response.update({"module": module_id, "items": result.items})
        if result.features:
            response["features"] = result.features
            response["features_hint"] = FEATURES_HINT
        if any(i.get("applies") for i in result.items + result.features):
            response["applies_hint"] = APPLIES_HINT
        if as_of:
            response["as_of"] = as_of
        if result.expanded:
            response["expanded"] = result.expanded
        if any(i.get("stale") for i in result.items + result.features):
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

    # ---- memory_graph ----

    @returns_errors
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
            return fail(f"{module_id}/{entity_id} 下没有记忆",
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

    # ---- list_modules ----

    @returns_errors
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
