"""模块规格：每个已登记模块一个目录，四份正文分开。

命令行只写骨架、模块索引里的事实和总目录。策划、美术、程序、现状由 pmem-spec 技能写入，这里不会整篇覆盖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pmem.core.registry import is_module_id, module_depth, parent_module

FACTS_START = "<!-- spec:facts:start -->"
FACTS_END = "<!-- spec:facts:end -->"
EMPTY = "<!-- spec:empty -->"
DESIGN_GAP = "<!-- spec:design-gap -->"
INDEX_MARKER = "<!-- 由 pmem spec index 生成目录；各模块正文请改对应的规格文件，重新运行会覆盖本文件 -->"
SECTIONS = ("策划设计", "美术设计", "程序设计", "模块现状")
CHECKED = ("程序设计", "模块现状")
__all__ = ["DESIGN_GAP", "EMPTY", "SECTIONS", "index_specs", "init_specs", "project_spec_dir"]


@dataclass
class SpecResult:
    written: int = 0
    skipped: int = 0
    blocked: list[str] = field(default_factory=list)
    index: Path | None = None


def project_spec_dir(root: Path, configured: str) -> Path | None:
    """配置里的 spec.dir 解析后必须仍在项目内。绝对路径、`..`、指到项目外的符号链接都拒绝。"""
    base = root.resolve()
    raw = Path(str(configured or ""))
    if not str(configured or "").strip():
        return None
    candidate = raw if raw.is_absolute() else base / raw
    try:
        resolved = candidate.resolve()
        resolved.relative_to(base)
    except (OSError, ValueError):
        return None
    return resolved


def _module_dir(out_dir: Path, module_id: str) -> Path | None:
    if not is_module_id(module_id) or module_id != Path(module_id).name or module_id in {".", ".."}:
        return None
    path = out_dir / module_id
    if path.is_symlink():
        return None
    try:
        resolved = path.resolve()
        resolved.relative_to(out_dir.resolve())
    except (OSError, ValueError):
        return None
    if resolved.parent != out_dir.resolve():
        return None
    return path


def _part_path(folder: Path, title: str) -> Path | None:
    if title not in SECTIONS:
        return None
    path = folder / f"{title}.md"
    if path.is_symlink() or path.name != f"{title}.md":
        return None
    return path


def _live(registry) -> list[str]:
    return sorted((mid for mid, module in registry.modules.items() if not module.merged_into), key=str.lower)


def _facts(module_id: str, registry) -> str:
    module = registry.modules.get(module_id)
    parent = parent_module(module_id)
    children = registry.children(module_id)
    paths = list(module.paths) if module is not None else []
    lines = [
        f"- 上级：{parent or '无'}",
        "- 下级：" + ("、".join(children) if children else "无"),
        "- 代码路径：" + ("、".join(f"`{p}`" for p in paths) if paths else "无"),
    ]
    return "\n".join(lines)


def _bodies() -> dict[str, str]:
    return {
        "策划设计": f"{DESIGN_GAP}\n首扫未从代码中看到的完整策划，此处留空。\n",
        "美术设计": (
            "无画面写「本模块无画面」。\n"
            "有画面时写风格、布局、各状态的画面、动效和资源规格；\n"
            "看不到的完整美术说明保留标记。\n"
            f"{DESIGN_GAP}\n"
        ),
        "程序设计": (
            f"{EMPTY}\n"
            "入口：\n"
            "入参字段闭集：\n"
            "出参字段闭集：\n"
            "数据形状与闭集词表：\n"
            "所有权：\n"
            "决定表：\n"
            "失败条件：\n"
            "配置与环境变量：\n"
            "关键流程：\n"
            "生成物：\n"
            "原文（须按字面抄）：\n"
        ),
        "模块现状": (
            f"{EMPTY}\n"
            "必须保持：\n"
            "一轮例子：\n"
            "单独拿走时还要带走的依赖规格：\n"
        ),
    }


def _part_doc(module_id: str, title: str, day: str, body: str) -> str:
    text = body.strip() + "\n"
    return f"---\nmodule: {module_id}\npart: {title}\nupdated: '{day}'\n---\n\n## {title}\n\n{text}"


def _module_index(module_id: str, registry) -> str:
    links = "\n".join(f"- [{title}]({title}.md)" for title in SECTIONS)
    return (
        f"---\nmodule: {module_id}\n---\n\n"
        f"{FACTS_START}\n{_facts(module_id, registry)}\n{FACTS_END}\n\n"
        f"{links}\n"
    )


def _section(text: str, title: str) -> str:
    marker = f"## {title}"
    start = text.find(marker)
    if start < 0:
        return ""
    rest = text[start + len(marker):]
    nxt = rest.find("\n## ")
    return rest if nxt < 0 else rest[:nxt]


def _updated(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("updated:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def _read(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return path.read_text(encoding="utf-8")


def _write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def status_of(folder: Path | None, deprecated: bool) -> str:
    if deprecated:
        return "不要求补"
    if folder is None or not folder.is_dir():
        return "无文件"
    for title in CHECKED:
        text = _read(folder / f"{title}.md")
        if text is None or EMPTY in text:
            return "首稿未完成"
    return "已有规格"


def gap_label(folder: Path | None) -> str:
    """目录上的提示。缺文件或仍有留空标记都标出来，不改变首稿是否完成。"""
    if folder is None or not folder.is_dir():
        return ""
    parts = []
    for title, missing, gap in (("策划设计", "缺策划节", "策划"), ("美术设计", "缺美术节", "美术")):
        text = _read(folder / f"{title}.md")
        if text is None:
            parts.append(missing)
        elif DESIGN_GAP in text:
            parts.append(gap)
    return "、".join(parts) if parts else "无"


def _latest(folder: Path) -> str:
    dates = [day for title in SECTIONS if (day := _updated(_read(folder / f"{title}.md") or ""))]
    return max(dates) if dates else ""


def _split_legacy(out_dir: Path, module_id: str, registry) -> bool:
    """把旧的单文件规格拆成目录。目录已存在时不动。"""
    legacy = out_dir / f"{module_id}.md"
    folder = _module_dir(out_dir, module_id)
    if folder is None or legacy.is_symlink() or not legacy.is_file() or folder.exists():
        return False
    text = legacy.read_text(encoding="utf-8")
    day = _updated(text) or date.today().isoformat()
    bodies = _bodies()
    for title in SECTIONS:
        body = _section(text, title).strip()
        part = _part_path(folder, title)
        if part is None:
            return False
        _write_new(part, _part_doc(module_id, title, day, body or bodies[title]))
    _write_new(folder / "index.md", _module_index(module_id, registry))
    legacy.unlink()
    return True


def _ensure(registry, out_dir: Path, module_id: str, day: str, fill_missing: bool) -> tuple[int, bool]:
    """返回 (新写的正文份数, 是否被拒绝)。fill_missing 为假时只拆旧文件、刷新索引。"""
    if _split_legacy(out_dir, module_id, registry):
        return 4, False
    legacy = out_dir / f"{module_id}.md"
    if legacy.is_symlink():
        return 0, True
    folder = _module_dir(out_dir, module_id)
    if folder is None:
        return 0, True
    if not fill_missing:
        if folder.is_dir() and not (folder / "index.md").is_symlink():
            text = _module_index(module_id, registry)
            if _read(folder / "index.md") != text:
                _write_new(folder / "index.md", text)
        return 0, False
    written = 0
    bodies = _bodies()
    for title in SECTIONS:
        path = _part_path(folder, title)
        if path is None:
            return written, True
        if path.exists():
            continue
        _write_new(path, _part_doc(module_id, title, day, bodies[title]))
        written += 1
    index = folder / "index.md"
    if index.is_symlink():
        return written, True
    if not index.exists():
        _write_new(index, _module_index(module_id, registry))
    return written, False


def _rows(registry, out_dir: Path) -> list[tuple[str, str, str, str]]:
    rows = []
    for module_id in _live(registry):
        module = registry.modules[module_id]
        folder = _module_dir(out_dir, module_id) if out_dir.is_dir() else None
        if folder is not None and not folder.is_dir():
            folder = None
        status = status_of(folder, module.deprecated)
        updated = _latest(folder) if folder is not None and folder.is_dir() else ""
        gap = "" if module.deprecated or status == "无文件" else gap_label(folder)
        rows.append((module_id, status, updated, gap))
    return rows


def init_specs(registry, out_dir: Path, day: str | None = None) -> SpecResult:
    day = day or date.today().isoformat()
    result = SpecResult()
    out_dir.mkdir(parents=True, exist_ok=True)
    for module_id in _live(registry):
        written, blocked = _ensure(registry, out_dir, module_id, day, fill_missing=True)
        if blocked:
            result.blocked.append(module_id)
            continue
        if written:
            result.written += 1
        else:
            result.skipped += 1
    return result


def index_specs(registry, out_dir: Path) -> SpecResult:
    result = SpecResult()
    out_dir.mkdir(parents=True, exist_ok=True)
    for module_id in _live(registry):
        written, blocked = _ensure(registry, out_dir, module_id, date.today().isoformat(), fill_missing=False)
        if blocked:
            result.blocked.append(module_id)
            continue
        result.written += written
    lines = [INDEX_MARKER, "# 模块规格", "",
             "每个模块一个目录，里边四份分开。这一页只是总目录。",
             "留空列只作提示：策划或美术仍留空、或还没有那一份。它不改变完成状态。", "",
             "| 模块 | 状态 | 留空 | 最近更新 |", "|---|---|---|---|"]
    for module_id, status, updated, gap in _rows(registry, out_dir):
        depth = module_depth(module_id)
        indent = "　" * (depth - 3) + "└ " if depth > 2 else ""
        folder = _module_dir(out_dir, module_id)
        label = f"[{module_id}]({module_id}/index.md)" if folder is not None and folder.is_dir() else module_id
        lines.append(f"| {indent}{label} | {status} | {gap} | {updated} |")
    lines.append("")
    index = out_dir / "index.md"
    index.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    result.index = index
    return result


def format_list(registry, out_dir: Path) -> str:
    rows = _rows(registry, out_dir) if out_dir.is_dir() else [
        (mid, status_of(None, registry.modules[mid].deprecated), "", "") for mid in _live(registry)]
    return "\n".join(f"{mid}  {status}" for mid, status, _, _ in rows)


def incomplete(registry, out_dir: Path) -> list[str]:
    rows = _rows(registry, out_dir) if out_dir.is_dir() else [
        (mid, status_of(None, registry.modules[mid].deprecated), "", "") for mid in _live(registry)]
    return [mid for mid, status, _, _ in rows if status in {"无文件", "首稿未完成"}]
