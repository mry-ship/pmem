"""严格的清理候选：只建议归档、不删除，由负责人确认。

候选的前提是“和代码已经对不上”：关联代码全部不存在，或没写关联代码、正文提到的文件和类在代码里几乎找不到。
关联代码还有一处在，就不算候选。
“建议归档”还须同时满足：同议题没有其他现行记忆、没有被其他记忆引用、统计期内本机没被用过
（本机检索太少时不看这一条）。只满足一部分的列为“待核对”；排除项、风险、更正、全项目级和种子记忆最多到“待核对”。
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from pmem.core.entry import PITFALL_KINDS, Entry
from pmem.core.ids import ULID_PATTERN
from pmem.index.graph import current_entries
from pmem.scan.files import FileIndex, code_mentions

MENTION_FOUND_MAX = 0.2
MIN_MENTIONS = 2
TOP = 10
_ULID = re.compile(rf"\b{ULID_PATTERN}\b")


def _anchors_gone(root: Path, entry: Entry) -> bool:
    return bool(entry.anchors) and not any((root / a.partition("#")[0].replace("\\", "/")).is_file()
                                           for a in entry.anchors)


def cleanup_candidates(root: Path, registry, entries: list[Entry], used: set[str] | None) -> dict:
    """entries 为全部记忆（含已替代、已归档）；used 为统计期内本机返回过的记忆 id，检索太少时传 None。"""
    current = current_entries(entries)
    referenced = {old for e in entries for old in e.supersedes}
    for e in entries:
        referenced.update(i for i in _ULID.findall(e.content) if i != e.id)
    topics = Counter((e.module, e.entity.lower()) for e in current)
    mentions = {e.id: code_mentions(e.content) for e in current}
    checkable = {e.id for e in current if len(mentions[e.id]) >= MIN_MENTIONS}
    paths_found: set[str] = set()
    classes: set[str] = set()
    if checkable:
        files = FileIndex(root, registry)
        wanted = [m for i in checkable for m in mentions[i]]
        paths_found = {raw for kind, raw in wanted if kind == "path" and files.candidates(raw)}
        classes = files.present_symbols({raw for kind, raw in wanted if kind == "class"})
    archive, review = [], []
    for entry in current:
        gone = _anchors_gone(root, entry)
        if entry.anchors and not gone:
            continue
        ratio = None
        if entry.id in checkable:
            hits = sum(raw in (paths_found if kind == "path" else classes) for kind, raw in mentions[entry.id])
            ratio = (hits, len(mentions[entry.id]))
        faded = ratio is not None and ratio[0] / ratio[1] < MENTION_FOUND_MAX
        if not (gone or faded):
            continue
        checks = [
            ("关联代码全部不存在", gone if entry.anchors else None),
            (f"正文提到的文件或类在代码里找到 {ratio[0]}/{ratio[1]}" if ratio else "正文没提到可核对的文件或类",
             faded if ratio else None),
            ("同议题没有其他现行记忆", topics[(entry.module, entry.entity.lower())] == 1),
            ("没有被其他记忆引用", entry.id not in referenced),
            ("统计期内本机没被用过", entry.id not in used if used is not None else None),
        ]
        met = all(ok for _, ok in checks if ok is not None) and gone and (faded or ratio is None)
        protected = entry.kind in PITFALL_KINDS or entry.project_wide or entry.status == "seed"
        basis = [f"{'✓' if ok else '✗'} {label}" for label, ok in checks if ok is not None]
        if protected:
            basis.append("排除项、风险、更正、全项目级和种子记忆不建议直接归档")
        row = {"id": entry.id, "module": entry.module, "entity": entry.entity, "kind": entry.kind,
               "title": entry.title, "basis": basis}
        (archive if met and not protected else review).append(row)
    return {"archive": archive, "review": review}
