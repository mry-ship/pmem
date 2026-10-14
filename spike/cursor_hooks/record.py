"""录制 Cursor Hook 的原始输入，仅用于 M0 实测。

用法：python spike/cursor_hooks/record.py <事件名>
- 保存 {事件名, 工作目录, 解释器, 原始输入} 到 spike/cursor_hooks/captures/<毫秒时间戳>_<事件名>.json
- 对 preToolUse：若目标是 pmem-spike 的 echo 工具，返回 updated_input 注入 injected 字段
- 其余事件一律输出 {}，不干预
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parent / "captures"


def _find_tool_input(data: dict) -> tuple[str, dict] | None:
    for key in ("tool_input", "arguments", "input", "params"):
        value = data.get(key)
        if isinstance(value, dict):
            return key, value
    return None


def _is_echo_tool(data: dict) -> bool:
    blob = json.dumps({k: data.get(k) for k in ("tool_name", "toolName", "name", "tool")}, ensure_ascii=False)
    return "echo" in blob.lower()


def main() -> None:
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    raw_bytes = sys.stdin.buffer.read()
    raw = raw_bytes.decode("utf-8", errors="replace")
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() * 1000)
    record = {
        "event": event,
        "cwd": os.getcwd(),
        "python": sys.executable,
        "ppid": os.getppid(),
        "comspec_shell": os.environ.get("PSModulePath", "")[:40],
        "head_hex": raw_bytes[:8].hex(),
        "raw": raw,
    }
    (CAPTURE_DIR / f"{stamp}_{event}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if event == "preToolUse":
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            data = {}
        found = _find_tool_input(data)
        if found and _is_echo_tool(data):
            _, tool_input = found
            updated = dict(tool_input)
            updated["injected"] = "FROM_HOOK"
            print(json.dumps({"permission": "allow", "updated_input": updated}, ensure_ascii=False))
            return
    print("{}")


if __name__ == "__main__":
    main()
