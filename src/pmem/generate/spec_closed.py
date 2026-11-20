"""规格闭集只读核对。

只判断写得成清单的字段名、原文整句和入口锚点。散文、必须保持的行为一律无法判断。
不写规格文件，也不产生「已确认不一致」。
"""
from __future__ import annotations

import re
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.generate.spec import _module_dir, _read
from pmem.index.anchors import symbol_block

_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.FORCEUNIX | wglob.IGNORECASE

_HEADINGS = ("入口", "入参字段闭集", "出参字段闭集", "原文（须按字面抄）", "必须保持")
_FIELD = re.compile(r"^\s*(?:[-*]\s+)?([A-Za-z_][\w.]*)\s*(?::\s*(\S.*?))?\s*$")
_ANCHOR = re.compile(r"((?:[\w.-]+/)+[\w.-]+\.\w+)(?:#([\w.:-]+))?")
_PLACEHOLDER = re.compile(r"<[^>\n]*>")
_STATUSES = ("一致", "可能不一致", "无法判断")


def closed_report(root: Path, registry: ModuleRegistry, out_dir: Path, module: str | None = None) -> dict:
    """对已登记模块做只读核对。module 给了但登记里没有时返回 error。"""
    if module:
        try:
            resolved = registry.resolve_module(module)
        except RegistryError:
            return {"error": f"没有模块 {module}"}
        if resolved.id not in registry.modules:
            return {"error": f"没有模块 {module}"}
        module_ids = [resolved.id]
    else:
        module_ids = [mid for mid, item in registry.modules.items() if not item.merged_into and not item.deprecated]
    modules = []
    for module_id in module_ids:
        folder = _module_dir(out_dir, module_id) if out_dir.is_dir() else None
        program = _read(folder / "程序设计.md") if folder is not None else None
        status = _read(folder / "模块现状.md") if folder is not None else None
        files = _module_texts(root, registry.modules[module_id].paths)
        sections = {**_sections(program or ""), **_sections(status or "")}
        items = _check_module(root, sections, files)
        modules.append({"module": module_id, "items": items})
    return {"modules": modules}


def format_closed(report: dict) -> str:
    lines: list[str] = []
    for module in report.get("modules") or []:
        lines.append(module["module"])
        items = module["items"]
        if not items:
            lines.append("  无法判断  没有程序设计或模块现状")
            continue
        for item in items:
            bits = [item["status"], item["section"]]
            if item.get("text"):
                bits.append(item["text"])
            if item.get("detail"):
                bits.append(item["detail"])
            lines.append("  " + "  ".join(bits))
    return "\n".join(lines)


def _sections(text: str) -> dict[str, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    current: str | None = None
    buckets: dict[str, list[str]] = {name: [] for name in _HEADINGS}
    for line in text.splitlines():
        name = line.strip().rstrip("：:")
        if name in buckets and line.strip().endswith(("：", ":")):
            current = name
            continue
        if current:
            buckets[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in buckets.items() if lines}


def _content_lines(body: str) -> list[str]:
    lines = []
    for line in body.splitlines():
        text = re.sub(r"^[-*]\s+", "", line.strip())
        if not text or text.startswith(("<!--", "（以下由")):
            continue
        lines.append(text)
    return lines


def _check_module(root: Path, sections: dict[str, str], files: list[tuple[Path, str]]) -> list[dict]:
    items: list[dict] = []
    for name in ("入参字段闭集", "出参字段闭集"):
        items.extend(_fields(name, sections.get(name, ""), files))
    items.extend(_sentences(sections.get("原文（须按字面抄）", ""), files))
    items.extend(_anchors(root, "入口", sections.get("入口", "")))
    for line in _content_lines(sections.get("必须保持", "")):
        items.append({
            "status": "无法判断",
            "section": "必须保持",
            "text": line,
            "detail": "原句仍在现状节；行为是否仍成立不判断",
        })
        items.extend(_anchors(root, "必须保持", line))
    if not sections:
        items.append({"status": "无法判断", "section": "规格", "detail": "没有程序设计或模块现状"})
    return [item for item in items if item["status"] in _STATUSES]


def _fields(section: str, body: str, files: list[tuple[Path, str]]) -> list[dict]:
    lines = _content_lines(body)
    if not lines:
        return [{"status": "无法判断", "section": section, "detail": "没有可核对的字段清单"}]
    parsed: list[tuple[str, str]] = []
    for line in lines:
        match = _FIELD.fullmatch(line)
        if match is None:
            return [{"status": "无法判断", "section": section, "detail": "不是一行一个字段名的清单"}]
        parsed.append((match.group(1), (match.group(2) or "").strip()))
    return [_one_field(section, name, signature, files) for name, signature in parsed]


def _one_field(section: str, name: str, signature: str, files: list[tuple[Path, str]]) -> dict:
    row = {"section": section, "text": name if not signature else f"{name}: {signature}"}
    if not files:
        row.update(status="无法判断", detail="模块没有可读取的代码文件")
        return row
    word = re.compile(rf"\b{re.escape(name)}\b")
    found = any(word.search(text) for _, text in files)
    annotations = [ann for path, text in files if path.suffix == ".py"
                   for ann in _param_annotations(text, name)]
    if signature:
        if not annotations:
            if found:
                row.update(status="无法判断", detail="代码里见过这个名字，但解析不出参数签名")
            else:
                row.update(status="可能不一致", detail="代码里找不到该字段名")
            return row
        norms = {_norm(ann) for ann in annotations}
        spec = _norm(signature)
        if len(norms) > 1:
            row.update(status="无法判断", detail="代码里该字段有多处不同签名")
        elif "" in norms:
            row.update(status="无法判断", detail="参数没有标注，对不上规格里的签名")
        elif spec in norms:
            row.update(status="一致")
        else:
            row.update(status="可能不一致", detail="名字在，签名对不上")
        return row
    if found:
        row.update(status="一致")
    else:
        row.update(status="可能不一致", detail="代码里找不到该字段名")
    return row


def _param_annotations(text: str, name: str) -> list[str]:
    import ast

    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        for extra in (node.args.vararg, node.args.kwarg):
            if extra is not None:
                args.append(extra)
        for arg in args:
            if arg.arg != name:
                continue
            found.append(ast.unparse(arg.annotation) if arg.annotation is not None else "")
    return found


def _sentences(body: str, files: list[tuple[Path, str]]) -> list[dict]:
    lines = _content_lines(body)
    if not lines:
        return [{"status": "无法判断", "section": "原文（须按字面抄）", "detail": "没有可按字面核对的整句"}]
    items = []
    blob = "\n".join(text for _, text in files)
    for line in lines:
        if _vague(line):
            items.append({"status": "无法判断", "section": "原文（须按字面抄）", "text": line,
                          "detail": "只写了含某某，不是整句"})
            continue
        if not files:
            items.append({"status": "无法判断", "section": "原文（须按字面抄）", "text": line,
                          "detail": "模块没有可读取的代码文件"})
            continue
        pattern = ".*?".join(re.escape(part) for part in _PLACEHOLDER.split(line))
        if re.search(pattern, blob, re.DOTALL):
            items.append({"status": "一致", "section": "原文（须按字面抄）", "text": line})
        else:
            items.append({"status": "可能不一致", "section": "原文（须按字面抄）", "text": line,
                          "detail": "整句在模块代码里对不上"})
    return items


def _vague(line: str) -> bool:
    if "<" in line or "含" not in line:
        return False
    rest = re.sub(r"含\S+", "", line).strip(" ：:，,。；;")
    return len(rest) < 8


def _anchors(root: Path, section: str, body: str) -> list[dict]:
    lines = _content_lines(body)
    found = [match for line in lines for match in _ANCHOR.finditer(line)]
    if section == "入口" and lines and not found:
        return [{"status": "无法判断", "section": section, "detail": "入口没有路径或路径#符号"}]
    if section == "入口" and not lines:
        return [{"status": "无法判断", "section": section, "detail": "没有可核对的入口锚点"}]
    items = []
    for match in found:
        rel, symbol = match.group(1), match.group(2) or ""
        items.append(_one_anchor(root, section, rel, symbol))
    return items


def _one_anchor(root: Path, section: str, rel: str, symbol: str) -> dict:
    label = f"{rel}#{symbol}" if symbol else rel
    row = {"section": section, "text": label}
    path = _inside(root, rel)
    if path is None:
        row.update(status="无法判断", detail="路径超出项目目录")
        return row
    if not path.is_file() or path.is_symlink():
        row.update(status="可能不一致", detail="路径不存在")
        return row
    if not symbol:
        row.update(status="一致")
        return row
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        row.update(status="无法判断", detail="符号取不出")
        return row
    if symbol_block(text, symbol) is None:
        row.update(status="可能不一致", detail="路径在，符号不在")
    else:
        row.update(status="一致")
    return row


def _inside(root: Path, rel: str) -> Path | None:
    rel = rel.replace("\\", "/").lstrip("/")
    if rel.startswith("../") or "/../" in f"/{rel}/":
        return None
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _module_texts(root: Path, patterns: list[str]) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for rel in wglob.glob(pattern, root_dir=root, flags=_GLOB):
            rel = str(rel).replace("\\", "/")
            path = _inside(root, rel)
            if path is None or not path.is_file() or path.is_symlink() or path in seen:
                continue
            if path.stat().st_size > 1_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if "\0" in text[:1024]:
                continue
            seen.add(path)
            found.append((path, text))
    return found


def _norm(text: str) -> str:
    return "".join(str(text).split()).casefold()
