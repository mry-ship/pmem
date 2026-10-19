"""本机事件日志：每行一个 JSON，只存在用户缓存目录，用于收益报告。"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

EVENTS_FILE = "events.jsonl"
# 单独的锁文件：Windows 的字节锁是强制锁，锁在日志本身上会让同时读日志的进程报错
LOCK_FILE = "events.lock"
MAX_BYTES = 20 * 1024 * 1024
# 统计期内本机检索少于这个次数时，“没被检索过”的模块和记忆不说明问题，报告里不列
MIN_SEARCHES_FOR_IDLE = 20


def log_event(cache_dir: Path, event_type: str, **fields) -> None:
    if os.environ.get("PMEM_NO_EVENTS"):
        return
    record = {"ts": round(time.time(), 3), "type": event_type, **{k: v for k, v in fields.items() if v is not None}}
    data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / EVENTS_FILE
        # 多个 pmem 进程（CLI、Hook、MCP 服务）会同时追加；Windows 的追加写不是原子的，不加锁会写坏行
        with _exclusive(cache_dir / LOCK_FILE):
            if path.exists() and path.stat().st_size > MAX_BYTES:
                try:
                    path.replace(path.with_suffix(".old.jsonl"))
                except OSError:
                    # Windows 上别的进程（report、health）正读着日志时改不了名，这次先照常追加，下次再轮转
                    pass
            with path.open("ab") as fh:
                fh.write(data)
    except OSError:
        pass


@contextmanager
def _exclusive(lock_path: Path) -> Iterator[None]:
    with lock_path.open("a+b") as fh:
        if os.name == "nt":
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)  # 拿不到会重试约 10 秒，仍失败抛 OSError
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)


def read_events(cache_dir: Path, since: float = 0.0) -> Iterator[dict]:
    for name in (EVENTS_FILE.replace(".jsonl", ".old.jsonl"), EVENTS_FILE):
        path = cache_dir / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("ts", 0) >= since:
                    yield record
