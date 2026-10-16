"""从记忆文件生成可浏览的模块 Wiki（Markdown）。

页面全部由记忆推出：每个模块一页，按议题列出现行结论，被替代的历史折叠起来，带关联代码和相关模块链接；
关联代码在记忆写下（或上次核对）之后改过的，标“需核实”。随时可以重新生成，不是第二份数据，不要手改。
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pmem.core.entry import Entry
from pmem.index.anchors import STALE_LABEL
from pmem.index.graph import KIND_LABELS, MemoryGraph, preview

MARKER = "<!-- 由 pmem wiki 从 .memory/entries 生成，重新运行会覆盖；要修改请改记忆本身 -->"
RECENT = 15
# 首次生成时放进目录：Wiki 是派生视图，默认不进版本库；删掉它就会被提交，之后也不会再生成
SELF_IGNORE = "*\n"


@dataclass
class WikiResult:
    pages: int
    written: int
    removed: int
    index: Path


def _page(module_id: str) -> str:
    return f"{module_id}.md"


def _kind(entry: Entry) -> str:
    return KIND_LABELS.get(entry.kind, entry.kind)


def _code_link(anchor: str, to_root: str) -> str:
    path, _, symbol = anchor.partition("#")
    path = path.replace("\\", "/")
    link = f"[{path}]({to_root}/{path})"
    return f"{link} `{symbol}`" if symbol else link


def _entry_block(entry: Entry, to_root: str, problems: list[str] | None) -> list[str]:
    title = f"### {_kind(entry)} · {entry.note_date} · {entry.author}"
    lines = [f"{title} · ⚠ {STALE_LABEL}" if problems else title, ""]
    if problems:
        lines += [f"> ⚠ {STALE_LABEL}：{'；'.join(problems)}。核对后仍成立就 confirm_memory，不成立就写 correction 替代。",
                  ""]
    lines += [entry.content.strip(), ""]
    meta = [f"id `{entry.id}`"]
    if entry.verified:
        meta.append(f"核对于 {entry.verified}")
    if entry.aliases:
        meta.append("也叫：" + "、".join(entry.aliases))
    lines.append(" · ".join(meta))
    if entry.anchors:
        lines += ["", "关联代码：" + "，".join(_code_link(a, to_root) for a in entry.anchors)]
    return [*lines, ""]


def _module_page(module_id: str, entries: list[Entry], graph: MemoryGraph, registry, to_root: str,
                 stale: dict[str, list[str]]) -> str:
    module = registry.modules.get(module_id)
    topics = graph.topics(module_id)
    current = [e for e in entries if e.id not in graph.superseded_by]
    lines = [MARKER, f"# {module_id}", "", "[← 全部模块](index.md)", ""]
    facts = []
    if module is not None and module.description:
        facts.append(module.description)
    if module is not None and module.aliases:
        facts.append("别名：" + "、".join(module.aliases))
    if module is not None and module.paths:
        facts.append("代码：" + "、".join(f"`{p}`" for p in module.paths))
    facts.append(f"现行记忆 {len(current)} 条，议题 {len(topics)} 个，最近更新 {max(e.note_date for e in entries)}")
    flagged = sum(1 for e in current if e.id in stale)
    if flagged:
        facts.append(f"⚠ {flagged} 条{STALE_LABEL}：关联代码在记忆写下后改过或已删除")
    lines += [*(f"- {f}" for f in facts), ""]

    related = graph.related(module_id, limit=10)
    if related:
        lines += ["## 相关模块", ""]
        for row in related:
            topics_hint = f"（对方议题：{'、'.join(row['entities'])}）" if row["entities"] else ""
            lines.append(f"- [{row['module']}]({_page(row['module'])})：{row['via']}{topics_hint}")
        lines.append("")

    by_topic: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        by_topic[entry.entity.lower()].append(entry)
    for topic in topics:
        items = by_topic[topic["entity"].lower()]
        live = sorted((e for e in items if e.id not in graph.superseded_by), key=lambda e: (e.note_date, e.id),
                      reverse=True)
        history = [e for e in items if e.id in graph.superseded_by]
        lines += [f"## {topic['entity']}", ""]
        for entry in live:
            lines += _entry_block(entry, to_root, stale.get(entry.id))
        if history:
            lines += [f"<details><summary>历史：{len(history)} 条已被替代</summary>", ""]
            for entry in history:
                newer = graph.superseded_by[entry.id]
                lines.append(f"- {entry.note_date} {_kind(entry)}：{preview(entry.content)}"
                             f" → {newer.note_date} 被 `{newer.id}` 替代")
            lines += ["", "</details>", ""]
    return "\n".join(lines).rstrip() + "\n"


def _index_page(title: str, by_module: dict[str, list[Entry]], graph: MemoryGraph, categories: list[str],
                stale: dict[str, list[str]]) -> str:
    current = graph.current
    lines = [MARKER, f"# {title} 研发记忆 Wiki", "",
             (f"共 {len(by_module)} 个模块、{len(current)} 条现行记忆，其中 {len(stale)} 条{STALE_LABEL}。"
              "每个模块一页，按议题列出现行结论。"), ""]
    by_category: dict[str, list[str]] = defaultdict(list)
    for module_id in by_module:
        by_category[module_id.split(".", 1)[0]].append(module_id)
    order = [c for c in categories if c in by_category] + sorted(c for c in by_category if c not in categories)
    for category in order:
        lines += [f"## {category}", "", f"| 模块 | 现行记忆 | 议题 | {STALE_LABEL} | 最近更新 |", "|---|---|---|---|---|"]
        for module_id in sorted(by_category[category]):
            entries = by_module[module_id]
            live = [e for e in entries if e.id not in graph.superseded_by]
            flagged = sum(1 for e in live if e.id in stale)
            lines.append(f"| [{module_id}]({_page(module_id)}) | {len(live)} | {len(graph.topics(module_id))} "
                         f"| {flagged or ''} | {max(e.note_date for e in entries)} |")
        lines.append("")
    lines += ["## 最近更新", ""]
    for entry in sorted(current, key=lambda e: (e.note_date, e.id), reverse=True)[:RECENT]:
        mark = f" ⚠ {STALE_LABEL}" if entry.id in stale else ""
        lines.append(f"- {entry.note_date} [{entry.module}]({_page(entry.module)}) · {entry.entity} · "
                     f"{_kind(entry)}{mark}：{preview(entry.content)}")
    return "\n".join(lines).rstrip() + "\n"


def render_wiki(service, out_dir: Path) -> dict[str, str]:
    """文件名 → 页面内容。"""
    graph = service.graph_model()
    stale = service.index.check_anchors(graph.current)
    by_module: dict[str, list[Entry]] = defaultdict(list)
    for entry in graph.entries:
        by_module[entry.module].append(entry)
    try:
        to_root = Path(os.path.relpath(service.root, out_dir)).as_posix()
    except ValueError:  # 不在同一个盘
        to_root = service.root.as_posix()
    pages = {_page(mid): _module_page(mid, entries, graph, service.registry, to_root, stale)
             for mid, entries in sorted(by_module.items())}
    title = service.config.get("project.name") or service.root.name
    pages["index.md"] = _index_page(title, by_module, graph, service.registry.categories, stale)
    return pages


def write_wiki(service, out_dir: Path) -> WikiResult:
    """生成并写入；内容没变的页面不重写，删掉不再对应模块、且由 pmem 生成的旧页面。"""
    out_dir = out_dir.resolve()
    pages = render_wiki(service, out_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
        (out_dir / ".gitignore").write_text(SELF_IGNORE, encoding="utf-8", newline="\n")
    written = 0
    for name, text in pages.items():
        path = out_dir / name
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8", newline="\n")
            written += 1
    removed = 0
    for path in out_dir.glob("*.md"):
        if path.name not in pages and path.read_text(encoding="utf-8", errors="replace").startswith(MARKER):
            path.unlink()
            removed += 1
    return WikiResult(len(pages), written, removed, out_dir / "index.md")
