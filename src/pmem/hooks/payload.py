"""解析 Cursor Hook 的标准输入。

Windows 中文系统上，Cursor 经 PowerShell 转发输入：UTF-8 字节先被按 GBK 解码，再以带 BOM 的 UTF-8 写出，
含中文时 JSON 常被破坏。因此按“原样 → GBK 回转 → 正则提取 ASCII 字段”三级兜底。
"""
from __future__ import annotations

import json
import re

_FIELDS = ("conversation_id", "generation_id", "hook_event_name", "tool_name", "status", "cwd", "prompt")
_INPUT_FIELDS = ("file_path", "command", "cwd", "module", "path", "entity", "query")


def _ungarble(text: str) -> str:
    try:
        return text.encode("gbk", errors="replace").decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return text


def _string_field(text: str, key: str) -> str | None:
    match = re.search(r'(?<!\\)"' + re.escape(key) + r'"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if not match:
        return None
    try:
        value = json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        value = match.group(1)
    if not value.isascii():
        repaired = _ungarble(value)
        if "\ufffd" not in repaired:
            value = repaired
    return value


def _extract(text: str) -> dict:
    data: dict = {}
    for key in _FIELDS:
        value = _string_field(text, key)
        if value is not None:
            data[key] = value
    head = text.split('"tool_input"', 1)
    inputs = {}
    if len(head) == 2:
        for key in _INPUT_FIELDS:
            value = _string_field(head[1], key)
            if value is not None:
                inputs[key] = value
        data["tool_input"] = inputs
    path = _string_field(text, "file_path")
    if path is not None:
        data["file_path"] = path
    if data:
        data["_partial"] = True
    return data


def parse_payload(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace").lstrip("\ufeff")
    candidates = [text]
    if not text.isascii():
        candidates.append(_ungarble(text))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return _extract(text)


def _garbled_patterns(needle: str) -> list[re.Pattern]:
    """needle 的 UTF-8 字节被按 GBK 误解码后可能呈现的样子（两种字节对齐），损坏处用通配。"""
    data = needle.encode("utf-8")
    patterns = []
    for offset in (0, 1, 2):
        chunk = data[offset:]
        if len(chunk) % 2:
            chunk = chunk[:-1]
        decoded = chunk.decode("gbk", errors="replace")
        pieces = [p for p in decoded.split("\ufffd") if p]
        if sum(len(p) for p in pieces) >= 2:
            patterns.append(re.compile(".{0,2}".join(re.escape(p) for p in pieces), re.DOTALL))
    return patterns


def fuzzy_contains(haystack: str, needle: str) -> bool:
    """在可能被转码损坏的文本里查找标记：原文、GBK 回转、按误解码形态三种方式。"""
    if not needle:
        return False
    if needle in haystack or needle in _ungarble(haystack):
        return True
    if needle.isascii():
        return False
    return any(p.search(haystack) for p in _garbled_patterns(needle))


def tool_input(data: dict) -> dict:
    value = data.get("tool_input")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def workspace_root(data: dict) -> str | None:
    roots = data.get("workspace_roots") or []
    if not roots:
        return None
    root = str(roots[0])
    if re.match(r"^/[A-Za-z]:", root):
        root = root[1:]
    return root
