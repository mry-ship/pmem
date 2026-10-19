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


def _fallback(event: str, agent: str) -> dict:
    if agent != "cursor":
        return {}
    if event in ("pre-tool", "before-mcp"):
        return {"permission": "allow"}
    return {"continue": True} if event == "prompt" else {}


def _find_project(payload: dict):
    from pmem.core.config import find_root
    from pmem.hooks.payload import workspace_root

    for candidate in (os.getcwd(), workspace_root(payload), payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")):
        if candidate and (root := find_root(candidate)) is not None:
            return root
    return None


def run_hook(event: str, agent: str = "cursor") -> int:
    fallback = _fallback(event, agent)
    root = None
    emitted = False
    try:
        from pmem.core.config import Config
        from pmem.hooks.agents import normalize, render
        from pmem.hooks.gate import handle
        from pmem.hooks.payload import parse_payload

        payload = normalize(agent, parse_payload(sys.stdin.buffer.read()))
        root = _find_project(payload)
        if root is None:
            _emit(fallback)
            return 0
        result = handle(event, payload, root)
        _emit(render(agent, event, result) or fallback)
        emitted = True
        if result.get("permission") == "deny" or result.get("followup_message") or result.get("updated_input"):
            tag = event if agent == "cursor" else f"{event}@{agent}"
            try:
                _log(Config.load(root).cache_dir, f"{tag} {json.dumps(result, ensure_ascii=False)[:300]}")
            except Exception:  # noqa: BLE001, S110  日志轮转撞车或文件被占用不能影响已输出的结果
                pass
    except Exception:  # noqa: BLE001
        # 只输出一次：两份 JSON 拼在一起 Cursor 解析不了，已给出的拦截结果也会作废
        if not emitted:
            _emit(fallback)
        try:
            from pmem.core.config import Config

            if root is not None:
                _log(Config.load(root).cache_dir, f"ERROR {event}@{agent}\n{traceback.format_exc()}", "hook-errors.log")
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
