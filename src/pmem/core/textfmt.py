from __future__ import annotations

import re

WRAP_WIDTH = 120
_MIN_PIECE = 6
_MAX_BRACKET_LINES = 3

_FENCE = re.compile(r"^\s*(```|~~~)")
_TABLE = re.compile(r"^\s*\|")
_LIST_PREFIX = re.compile(r"^(\s*(?:[-*+]|\d{1,2}[.)）、])\s+)")
_ENUM_START = re.compile(r"^(?:\d{1,2}[)）、]|\d{1,2}\.(?!\d)|[（(]\d{1,2}[)）]|[①-⑳])")
# 句末标点后断开；后面紧跟右引号、右括号或另一个标点时不断
_SENTENCE_END = re.compile(r"(?<=[。！？；])(?=[^\s。！？；，、”’」』）)\]】])")
# 行内编号（“：1) …；2) …”）之前断开
_INLINE_ENUM = re.compile(
    r"(?<=[：:；;。，,])\s*(?=(?:\d{1,2}[)）]|\d{1,2}、|\d{1,2}\.(?!\d)|[（(]\d{1,2}[)）]|[①-⑳])\s*\S)"
)


def format_content(text: str, width: int = WRAP_WIDTH) -> str:
    """把过长的行按句号、分号和行内编号断开，行内编号另起一行并缩进两格，便于直接阅读记忆文件。
    只增加换行和缩进，不改文字；代码块和表格不动；重复调用结果不变。"""
    out: list[str] = []
    in_fence = False
    for line in _join_bracket_splits(text.replace("\r\n", "\n").split("\n")):
        if _FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or len(line) <= width or _TABLE.match(line):
            out.append(line)
            continue
        out.extend(_wrap_line(line))
    return "\n".join(out).strip()


def _join_bracket_splits(lines: list[str]) -> list[str]:
    """并回括号里被断开的行（早期版本会在括注里的分号后断行）。
    几行之内闭合不了的括号（区间 (0, 1]、表情 :( ）不是被断开的，原样保留。"""
    joined: list[str] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and _unclosed(line):
            merged, j = line, i + 1
            while j < len(lines) and j - i <= _MAX_BRACKET_LINES and _continues(lines[j]) and _unclosed(merged):
                merged += lines[j].strip()
                j += 1
            if j > i + 1 and not _unclosed(merged):
                joined.append(merged)
                i = j
                continue
        joined.append(line)
        i += 1
    return joined


def _continues(line: str) -> bool:
    return bool(line.strip()) and not _FENCE.match(line) and not _LIST_PREFIX.match(line) \
        and not _ENUM_START.match(line.strip())


def _wrap_line(line: str) -> list[str]:
    match = _LIST_PREFIX.match(line)
    prefix = match.group(1) if match else ""
    indent = " " * len(prefix) if prefix else ""
    body = line[len(prefix):]
    marked = _SENTENCE_END.sub("\n", _INLINE_ENUM.sub("\n", body))
    pieces: list[str] = []
    for piece in (p.strip() for p in marked.split("\n")):
        if not piece:
            continue
        if pieces and (_unclosed(pieces[-1]) or len(piece) < _MIN_PIECE and not _ENUM_START.match(piece)):
            pieces[-1] += piece
        else:
            pieces.append(piece)
    if len(pieces) <= 1:
        return [line]
    rest = [indent + ("  " if _ENUM_START.match(p) else "") + p for p in pieces[1:]]
    return [prefix + pieces[0], *rest]


def _unclosed(text: str) -> bool:
    """括号还没闭合时不断行，免得把一句括注拆到两行。"""
    return text.count("（") + text.count("(") > text.count("）") + text.count(")")
