"""检索类操作：search_memory、memory_graph、list_modules。只读，不改记忆文件。"""
from __future__ import annotations

import time

from pmem.service.base import MAX_LIMIT, VERIFY_HINT, ServiceBase, fail, returns_errors, valid_date

MAX_RELATED = 3


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
    ) -> dict:
        started = time.perf_counter()
        try:
            response = self._search(module, path, entity, query, limit, valid_date(as_of))
        except ValueError as exc:  # 含 RegistryError
            response = fail(str(exc))
        items = response.get("items") or []
        self._log(
            "search",
            conv=source_conversation,
            ok=response.get("ok"),
            module=response.get("module"),
            path=(path or None) and self._relative(path),
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
