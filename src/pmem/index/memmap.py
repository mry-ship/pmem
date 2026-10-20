"""记忆图的数据：按模块分区、模块内按议题排时间线，只从记忆文件推出，不读版本库。

- 节点按类型分四组：失败或纠错（排除项、更正）、落地（结论、决定、功能）、注意（风险）、未实现（规划）；
- 边：supersedes 是实线（记忆里写明的替代）；同议题里排除项之后第一条落地的记忆是虚线，标明是推断；
- 悬而未决：议题里最后一条排除项之后没有任何落地的记忆，且这条排除项还现行。
"""
from __future__ import annotations

from collections import defaultdict

from pmem.core.entry import KIND_LABELS, VISIBLE_STATUSES, Entry

GROUPS = {"exclusion": "fail", "correction": "fail", "conclusion": "landed", "decision": "landed",
          "feature": "landed", "risk": "caution", "plan": "pending"}
GROUP_LABELS = {"fail": "失败或纠错", "landed": "落地", "caution": "注意", "pending": "未实现"}
LANDED_KINDS = tuple(k for k, g in GROUPS.items() if g == "landed")


def _order(e: Entry) -> tuple[str, str]:
    return e.note_date, e.id


def _node(e: Entry, superseded_by: dict[str, str], full: bool) -> dict:
    node = {"id": e.id, "kind": e.kind, "label": KIND_LABELS.get(e.kind, e.kind), "group": GROUPS.get(e.kind, "landed"),
            "date": e.note_date, "author": e.author, "title": e.title, "status": e.status,
            "current": e.status in VISIBLE_STATUSES and e.id not in superseded_by}
    if e.id in superseded_by:
        node["superseded_by"] = superseded_by[e.id]
    if e.reverted_on:
        node["reverted"] = e.reverted_on
    if e.project_wide:
        node["project"] = True
    if full:
        node["content"] = e.content
        if e.anchors:
            node["anchors"] = list(e.anchors)
        if e.applies:
            node["applies"] = e.applies
    return node


def _inferred(items: list[Entry], explicit: set[tuple[str, str]]) -> list[dict]:
    """排除项之后同议题第一条落地的记忆：多半是排除之后找到的做法，但没写替代关系，所以只是推断。"""
    edges = []
    for i, entry in enumerate(items):
        if entry.kind != "exclusion":
            continue
        landed = next((e for e in items[i + 1:] if e.kind in LANDED_KINDS), None)
        if landed is not None and (entry.id, landed.id) not in explicit:
            edges.append({"from": entry.id, "to": landed.id, "type": "inferred"})
    return edges


def unresolved(items: list[Entry], current: set[str]) -> Entry | None:
    """议题里最后一条排除项之后没有落地的记忆（且它还现行）：只知道哪些路不通，不知道最后怎么做的。"""
    last = max((i for i, e in enumerate(items) if e.kind == "exclusion"), default=None)
    if last is None or items[last].id not in current:
        return None
    return None if any(e.kind in LANDED_KINDS for e in items[last + 1:]) else items[last]


def build_map(entries: list[Entry], full: bool = True) -> dict:
    """entries 应包含已归档、已被替代的记忆，图上才看得到完整演化。full=False 时节点不带正文（Wiki 用）。"""
    superseded_by: dict[str, str] = {}
    for e in sorted(entries, key=_order):
        for old in e.replaces():
            superseded_by.setdefault(old, e.id)
    current = {e.id for e in entries if e.status in VISIBLE_STATUSES and e.id not in superseded_by}
    known = {e.id for e in entries}
    topics: dict[str, dict[str, list[Entry]]] = defaultdict(lambda: defaultdict(list))
    names: dict[tuple[str, str], str] = {}
    for e in sorted(entries, key=_order):
        topics[e.module][e.entity.lower()].append(e)
        names[(e.module, e.entity.lower())] = e.entity
    modules = []
    for module in sorted(topics):
        rows = []
        for key, items in topics[module].items():
            explicit = [{"from": old, "to": e.id, "type": "supersedes"}
                        for e in items for old in e.supersedes if old in known]
            for edge in explicit:
                if edge["to"] in {e.id for e in items if e.reverted_on}:
                    edge["type"] = "reverted"
            pairs = {(edge["from"], edge["to"]) for edge in explicit}
            stuck = unresolved(items, current)
            rows.append({
                "entity": names[(module, key)],
                "nodes": [_node(e, superseded_by, full) for e in items],
                "edges": explicit + _inferred(items, pairs),
                "current": sum(e.id in current for e in items),
                "last": items[-1].note_date,
                "unresolved": stuck.id if stuck else None,
            })
        rows.sort(key=lambda r: (r["last"], r["entity"].lower()), reverse=True)
        modules.append({"module": module, "topics": rows, "current": sum(r["current"] for r in rows),
                        "total": sum(len(r["nodes"]) for r in rows)})
    return {"modules": modules, "current": len(current), "total": len(entries)}
