from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

TTL_SECONDS = 7 * 24 * 3600
LOCK_TIMEOUT = 5.0
_LOCK_POLL = 0.02
REPLACE_RETRIES = 5
_DEFAULTS = {
    "searched": [], "warned": [], "edited": [], "written": {}, "nudged": [], "skip": False,
    "returned": [], "recorded": [], "cli_recorded": [], "edited_files": [],
    "consulted": [], "analysis": False,
    # 提问审查：本对话里 Agent 看过记忆（检索过或收到过摘要）的模块、最近一次提问提到的模块
    "reviewed": [], "asked": [], "review_nudged": [], "skip_reason": "", "skip_noticed": False,
    # 终端命令执行前未提交文件的快照（命令摘要 → {路径 → [mtime_ns, size]}），执行后比对出命令实际改了哪些文件
    "shell_before": {}, "late_warned": [],
}


def _try_lock(fh) -> bool:
    try:
        if os.name == "nt":
            import msvcrt

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fh) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


class SessionState:
    """单个对话的闸门状态，存放在用户缓存目录，按对话 id 隔离。"""

    def __init__(self, cache_dir: Path, conversation_id: str):
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", conversation_id)[:80]
        self.dir = cache_dir / "sessions"
        self.path = self.dir / f"{safe}.json"
        self.data = self._load()

    def _load(self) -> dict:
        data = {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in _DEFAULTS.items()}
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                saved = None
            # 文件损坏（null、数组、字段类型不对）时逐项丢弃，否则这个对话的 Hook 会一直出错、默认放行
            if isinstance(saved, dict):
                for key, value in saved.items():
                    default = _DEFAULTS.get(key)
                    if default is None or isinstance(value, type(default)):
                        data[key] = value
        return data

    @contextmanager
    def locked(self) -> Iterator[SessionState]:
        """同一对话的 Hook 会并行执行（Cursor 并行发出的工具调用各起一个进程），读、改、写必须串行，
        否则后写的会覆盖先写的。等锁超时就不加锁继续，宁可偶尔丢一次更新，也不卡住开发。"""
        self.dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(".lock")
        with open(lock_path, "a+b") as fh:
            deadline = time.monotonic() + LOCK_TIMEOUT
            held = _try_lock(fh)
            while not held and time.monotonic() < deadline:
                time.sleep(_LOCK_POLL)
                held = _try_lock(fh)
            if held:
                # 锁文件从不写入，按修改时间清理会删掉活跃对话正持有的锁
                try:
                    os.utime(lock_path)
                except OSError:
                    pass
            try:
                self.data = self._load()
                yield self
            finally:
                if held:
                    _unlock(fh)

    def add(self, key: str, value: str) -> None:
        if value not in self.data[key]:
            self.data[key].append(value)

    def has(self, key: str, value: str) -> bool:
        return value in self.data[key]

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        # Windows 上目标文件正被别的 Hook 进程读着时 os.replace 会报 PermissionError，稍等重试
        for attempt in range(REPLACE_RETRIES):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if attempt == REPLACE_RETRIES - 1:
                    tmp.unlink(missing_ok=True)
                    raise
                time.sleep(_LOCK_POLL)

    def cleanup_old(self) -> None:
        cutoff = time.time() - TTL_SECONDS
        for pattern in ("*.json", "*.lock", "*.tmp"):
            for path in self.dir.glob(pattern):
                try:
                    if path.stat().st_mtime < cutoff:
                        path.unlink()
                except OSError:
                    pass
