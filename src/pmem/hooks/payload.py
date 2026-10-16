"""解析 Cursor Hook 的标准输入。

Windows 中文系统上，Cursor 经 PowerShell 转发输入：UTF-8 字节先被按 GBK 解码，再以带 BOM 的 UTF-8 写出，
含中文时 JSON 常被破坏。因此按“原样 → GBK 回转 → 正则提取 ASCII 字段”三级兜底。
"""
from __future__ import annotations

import json
import re

_FIELDS = ("conversation_id", "generation_id", "hook_event_name", "tool_name", "status", "cwd", "prompt",
           "transcript_path")
_TRANSCRIPT_TAIL = 512 * 1024
_USER_QUERY = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
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


_NEGATIONS = ("不", "别", "勿", "没", "避免", "防止", "如何", "怎么", "是否")
# 紧跟在标记后面仍算“要求跳过”的语气词；跟着别的字（如“跳过记忆审查”“跳过记忆的逻辑”）是在谈论这件事
_PARTICLES = set("吧了呀啊哈呢嘛")


def _standalone(text: str, start: int, marker: str) -> bool:
    after = text[start + len(marker):start + len(marker) + 1]
    if after and after.isalnum() and after not in _PARTICLES:
        return False
    before = text[max(0, start - 4):start]
    return not any(word in before for word in _NEGATIONS)


def readable(text: str, marker: str) -> str:
    """原文或反解乱码后的文本里，能找到 marker 的那一份；都找不到时返回原文。"""
    fixed = _ungarble(text)
    return fixed if marker not in text and marker in fixed else text


def asks_to_skip(text: str, marker: str) -> bool:
    """用户是在要求跳过（“这次跳过记忆”），而不是在谈论它（“避免跳过记忆审查”“不要跳过记忆”）。"""
    if not marker:
        return False
    for candidate in (text, _ungarble(text)):
        starts = [m.start() for m in re.finditer(re.escape(marker), candidate)]
        if starts:
            return any(_standalone(candidate, i, marker) for i in starts)
    # 只剩误解码形态时看不清上下文，按出现即算
    return fuzzy_contains(text, marker)


def tool_input(data: dict) -> dict:
    value = data.get("tool_input")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _local_path(raw: str) -> str:
    """Cursor 把 Windows 路径写成 /c:/Users/...。"""
    return raw[1:] if re.match(r"^/[A-Za-z]:", raw) else raw


def workspace_root(data: dict) -> str | None:
    roots = data.get("workspace_roots") or []
    return _local_path(str(roots[0])) if roots else None


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(block.get("text") or "") for block in content
                         if isinstance(block, dict) and block.get("type") == "text")
    return ""


def last_user_text(transcript_path: str | None) -> str | None:
    """对话记录（JSONL，UTF-8，不受 Hook 转码影响）里最后一条用户消息的文字。
    Cursor 的消息里还夹着附件和系统提示，只取 <user_query> 里的部分；读不到时返回 None。"""
    if not transcript_path:
        return None
    try:
        with open(_local_path(str(transcript_path)), "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - _TRANSCRIPT_TAIL))
            lines = fh.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        message = record.get("message") if isinstance(record.get("message"), dict) else {}
        if (record.get("role") or message.get("role") or record.get("type")) != "user":
            continue
        # Claude Code 把工具结果也记成 user 消息，它们没有 text 块
        text = _text_of(message.get("content", record.get("content")))
        if text.strip():
            query = _USER_QUERY.search(text)
            return query.group(1) if query else text
    return None
