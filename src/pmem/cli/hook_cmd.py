from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path


def _emit(data: dict) -> None:
    # 纯 ASCII 输出：Windows 下经 PowerShell 转发时不会被转码破坏
    sys.stdout.write(json.dumps(data, ensure_ascii=True))
    sys.stdout.flush()


def run_hook(event: str) -> int:
    fallback = {"permission": "allow"} if event in ("pre-tool", "before-mcp") else {}
    if event == "prompt":
        fallback = {"continue": True}
    root = None
    try:
        from pmem.core.config import Config, find_root
        from pmem.hooks.gate import handle
        from pmem.hooks.payload import parse_payload, workspace_root

        payload = parse_payload(sys.stdin.buffer.read())
        root = find_root(os.getcwd())
        if root is None and (ws := workspace_root(payload)):
            root = find_root(ws)
        if root is None:
            _emit(fallback)
            return 0
        result = handle(event, payload, root)
        _emit(result or fallback)
        if result.get("permission") == "deny" or result.get("followup_message") or result.get("updated_input"):
            _log(Config.load(root).cache_dir, f"{event} {json.dumps(result, ensure_ascii=False)[:300]}")
    except Exception:  # noqa: BLE001
        _emit(fallback)
        try:
            from pmem.core.config import Config

            if root is not None:
                _log(Config.load(root).cache_dir, f"ERROR {event}\n{traceback.format_exc()}", "hook-errors.log")
        except Exception:  # noqa: BLE001, S110
            pass
    return 0


def _log(cache_dir: Path, line: str, name: str = "hooks.log") -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / name
    if path.exists() and path.stat().st_size > 512 * 1024:
        path.replace(path.with_suffix(".old.log"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
