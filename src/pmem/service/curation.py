"""整理用的只读统计：高频词（找同义说法）、可合并的议题分组与组内全文。"""
from __future__ import annotations

from collections import Counter

from pmem.core.entry import Entry
from pmem.index.tokenize import tokenize
from pmem.service.base import ServiceBase, fail, returns_errors

COMPACT_MIN_GROUP = 5


class CurationOps(ServiceBase):
    # ---- terms ----

    @returns_errors
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

    # ---- compact ----

    def _topic_groups(self, module: str | None = None) -> dict[tuple[str, str], list[Entry]]:
        """按 (模块, 议题) 分组的有效记忆，组内从旧到新。"""
        groups: dict[tuple[str, str], list[Entry]] = {}
        for entry in sorted(self.index.visible(), key=lambda e: (e.note_date, e.id)):
            if module and entry.module.lower() != module.lower():
                continue
            groups.setdefault((entry.module, entry.entity.lower()), []).append(entry)
        return groups

    @returns_errors
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

    @returns_errors
    def compact_group(self, module: str, entity: str) -> dict:
        """一个议题下全部有效记忆的正文（从旧到新），供合并成一条。"""
        module_id = self._module_id(module)
        entity_id = self.registry.resolve_entity(module_id, entity)
        items = self._topic_groups(module_id).get((module_id, entity_id.lower()), [])
        if not items:
            return fail(f"{module_id}/{entity_id} 下没有有效记忆")
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
