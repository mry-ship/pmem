"""轻量知识图谱：不新增存储，从已有记忆推出三类关系。

- 时间：同一议题（模块 + 实体）下的记忆按日期排成时间线，supersedes 给出“从哪天起被谁替代”；
- 共享代码：两条记忆关联同一个文件，或记忆关联的文件属于另一个模块；
- 正文提及：记忆正文写到了另一个模块的名字或别名。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from pmem.core.entry import Entry
from pmem.core.registry import ModuleRegistry, RegistryError

VISIBLE = ("active", "seed", "draft")
REPLACING = (*VISIBLE, "archived")
PREVIEW_CHARS = 80
LATEST_PER_TOPIC = 2
KIND_LABELS = {"exclusion": "排除项", "risk": "风险", "correction": "更正", "decision": "决定", "conclusion": "结论"}
# 先看的顺序：排除项、风险最能避免走弯路
KIND_ORDER = {kind: i for i, kind in enumerate(KIND_LABELS)}


def preview(text: str, limit: int = PREVIEW_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def current_entries(entries: list[Entry]) -> list[Entry]:
    """可见且没有被替代的记忆，从新到旧。"""
    visible = [e for e in entries if e.status in VISIBLE]
    replaced = {old for e in entries if e.status in REPLACING for old in e.supersedes}
    return sorted((e for e in visible if e.id not in replaced), key=lambda e: (e.note_date, e.id), reverse=True)


def digest(entries: list[Entry], limit: int = 6, per_topic: int = 2) -> list[Entry]:
    """一个模块最值得先看的现行记忆：排除项、风险、更正、决定在前，同类从新到旧，每个议题最多 per_topic 条。"""
    picked: list[Entry] = []
    per: Counter = Counter()
    for entry in sorted(current_entries(entries), key=lambda e: KIND_ORDER.get(e.kind, len(KIND_ORDER))):
        if per[entry.entity.lower()] < per_topic:
            picked.append(entry)
            per[entry.entity.lower()] += 1
        if len(picked) == limit:
            break
    return picked


@dataclass
class Link:
    code: int = 0
    mention: int = 0
    files: list[str] = field(default_factory=list)
    entities: Counter = field(default_factory=Counter)

    def describe(self) -> str:
        parts = [f"共享代码 {self.code}" if self.code else "", f"正文提及 {self.mention}" if self.mention else ""]
        return "、".join(p for p in parts if p)


class MemoryGraph:
    def __init__(self, entries: list[Entry], registry: ModuleRegistry):
        self.registry = registry
        self.entries = sorted((e for e in entries if e.status in VISIBLE), key=lambda e: (e.note_date, e.id))
        self.superseded_by: dict[str, Entry] = {}
        replacing = sorted((e for e in entries if e.status in REPLACING), key=lambda e: (e.note_date, e.id))
        for entry in replacing:
            for old in entry.supersedes:
                self.superseded_by.setdefault(old, entry)
        self.current = [e for e in self.entries if e.id not in self.superseded_by]
        self._patterns = registry.name_patterns()
        # (模块, 实体小写) → 对端模块 → 关系
        self.links: dict[tuple[str, str], dict[str, Link]] = defaultdict(dict)
        self._build()

    def _owner(self, rel: str) -> str | None:
        try:
            match = self.registry.module_for_path(rel)
        except RegistryError:
            return None
        return match.module_id if match else None

    def _link(self, entry: Entry, other_module: str, kind: str, other_entity: str | None = None,
              file: str | None = None) -> None:
        if other_module == entry.module:
            return
        for (module, entity), target, target_entity in (
            ((entry.module, entry.entity.lower()), other_module, other_entity),
            ((other_module, (other_entity or "").lower()), entry.module, entry.entity),
        ):
            link = self.links[(module, entity)].setdefault(target, Link())
            setattr(link, kind, getattr(link, kind) + 1)
            if file and file not in link.files:
                link.files.append(file)
            if target_entity:
                link.entities[target_entity] += 1

    def _build(self) -> None:
        by_file: dict[str, list[Entry]] = defaultdict(list)
        for entry in self.current:
            for anchor in entry.anchors:
                rel = anchor.partition("#")[0].replace("\\", "/")
                by_file[rel].append(entry)
                owner = self._owner(rel)
                if owner:
                    self._link(entry, owner, "code", file=rel)
            for mid, pattern in self._patterns.items():
                if mid != entry.module and pattern.search(entry.content):
                    self._link(entry, mid, "mention")
        for rel, group in by_file.items():
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    if a.module != b.module:
                        self._link(a, b.module, "code", other_entity=b.entity, file=rel)

    # ---- 查询 ----

    def related(self, module: str, entity: str | None = None, limit: int = 5) -> list[dict]:
        merged: dict[str, Link] = {}
        for (mid, ent), targets in self.links.items():
            if mid != module or (entity and ent != entity.lower()):
                continue
            for target, link in targets.items():
                total = merged.setdefault(target, Link())
                total.code += link.code
                total.mention += link.mention
                total.files += [f for f in link.files if f not in total.files]
                total.entities.update(link.entities)
        rows = sorted(merged.items(), key=lambda kv: (-(kv[1].code + kv[1].mention), kv[0]))[:limit]
        return [
            {"module": target, "via": link.describe(), "files": link.files[:3],
             "entities": [e for e, _ in link.entities.most_common(3)]}
            for target, link in rows
        ]

    def timeline(self, module: str, entity: str) -> list[dict]:
        rows = []
        for entry in self.entries:
            if entry.module != module or entry.entity.lower() != entity.lower():
                continue
            row = {"id": entry.id, "date": entry.note_date, "kind": entry.kind, "author": entry.author,
                   "preview": preview(entry.content)}
            newer = self.superseded_by.get(entry.id)
            if newer is not None:
                row["superseded_by"] = newer.id
                row["until"] = newer.note_date
            if entry.supersedes:
                row["replaces"] = list(entry.supersedes)
            rows.append(row)
        return rows

    def topics(self, module: str) -> list[dict]:
        groups: dict[str, list[Entry]] = defaultdict(list)
        names: dict[str, str] = {}
        for entry in self.entries:
            if entry.module == module:
                groups[entry.entity.lower()].append(entry)
                names[entry.entity.lower()] = entry.entity
        rows = []
        for key, items in groups.items():
            current = [e for e in items if e.id not in self.superseded_by]
            rows.append({
                "entity": names[key],
                "current": len(current),
                "superseded": len(items) - len(current),
                "first": items[0].note_date,
                "last": items[-1].note_date,
                "kinds": dict(Counter(e.kind for e in current)),
                "latest": [{"id": e.id, "kind": e.kind, "date": e.note_date, "preview": preview(e.content)}
                           for e in reversed(current[-LATEST_PER_TOPIC:])],
            })
        rows.sort(key=lambda r: (r["last"], r["current"]), reverse=True)
        return rows
