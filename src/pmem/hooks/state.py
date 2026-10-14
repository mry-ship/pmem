from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

TTL_SECONDS = 7 * 24 * 3600
_DEFAULTS = {
    "searched": [], "warned": [], "edited": [], "written": {}, "nudged": [], "skip": False,
    "returned": [], "recorded": [], "cli_recorded": [], "edited_files": [],
}


class SessionState:
    """单个对话的闸门状态，存放在用户缓存目录，按对话 id 隔离。"""

    def __init__(self, cache_dir: Path, conversation_id: str):
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", conversation_id)[:80]
        self.dir = cache_dir / "sessions"
        self.path = self.dir / f"{safe}.json"
        self.data = {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in _DEFAULTS.items()}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass

    def add(self, key: str, value: str) -> None:
        if value not in self.data[key]:
            self.data[key].append(value)

    def has(self, key: str, value: str) -> bool:
        return value in self.data[key]

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def cleanup_old(self) -> None:
        cutoff = time.time() - TTL_SECONDS
        for path in self.dir.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass
