"""对话内去重：记下每个对话已经返回过全文的记忆，再次检索到时只给 id 和标题，不重复正文。

记在用户缓存目录 seen/<对话>.txt，一行一个 id，服务（MCP、命令行）写、Hook 在上下文压缩后清空。
终端里的 pmem search 拿不到对话 id：Hook 在命令执行前把对话 id 和要查的模块写进交接文件，
命令行在短时间窗内按模块认领。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from pmem.core.fileio import write_atomic

SEEN_DIR = "seen"
HANDOFF_FILE = "cli-handoff.json"
HANDOFF_WINDOW = 120
MAX_HANDOFFS = 8
TTL_SECONDS = 7 * 24 * 3600


def _file(cache_dir: Path, conversation: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", conversation)[:80]
    return cache_dir / SEEN_DIR / f"{safe}.txt"


def load(cache_dir: Path | None, conversation: str | None) -> set[str]:
    if not cache_dir or not conversation:
        return set()
    try:
        text = _file(cache_dir, conversation).read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line.strip() for line in text.splitlines() if line.strip()}


def add(cache_dir: Path | None, conversation: str | None, ids: list[str]) -> None:
    if not cache_dir or not conversation or not ids:
        return
    path = _file(cache_dir, conversation)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("".join(f"{i}\n" for i in ids))
    except OSError:
        pass


def clear(cache_dir: Path | None, conversation: str | None) -> None:
    if not cache_dir or not conversation:
        return
    try:
        _file(cache_dir, conversation).unlink(missing_ok=True)
    except OSError:
        pass


def cleanup_old(cache_dir: Path) -> None:
    cutoff = time.time() - TTL_SECONDS
    for path in (cache_dir / SEEN_DIR).glob("*.txt"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def _handoffs(cache_dir: Path) -> list[dict]:
    try:
        data = json.loads((cache_dir / SEEN_DIR / HANDOFF_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def note_handoff(cache_dir: Path, conversation: str, modules: list[str]) -> None:
    """Hook：终端命令里有 pmem search 时，执行前登记“哪个对话要查哪些模块”。"""
    if not conversation:
        return
    now = time.time()
    rows = [d for d in _handoffs(cache_dir) if now - _ts(d) < HANDOFF_WINDOW]
    rows.append({"conv": conversation, "ts": now, "modules": [m.lower() for m in modules]})
    try:
        (cache_dir / SEEN_DIR).mkdir(parents=True, exist_ok=True)
        write_atomic(cache_dir / SEEN_DIR / HANDOFF_FILE, json.dumps(rows[-MAX_HANDOFFS:], ensure_ascii=False))
    except OSError:
        pass


def claim_handoff(cache_dir: Path | None, module: str | None) -> str | None:
    """命令行：认领最近登记的对话。指定了模块时只认登记过该模块的；没指定模块（全局检索）时只认没登记模块的。
    两个对话恰好同时在终端查同一模块时可能认错，后果只是对方少显示几条正文。"""
    if not cache_dir:
        return None
    now = time.time()
    wanted = module.lower() if module else None
    for row in reversed(_handoffs(cache_dir)):
        if now - _ts(row) >= HANDOFF_WINDOW:
            continue
        modules = row.get("modules") or []
        if (wanted in modules) if wanted else not modules:
            return str(row.get("conv") or "") or None
    return None


def _ts(row: dict) -> float:
    try:
        return float(row.get("ts") or 0)
    except (TypeError, ValueError):
        return 0.0
