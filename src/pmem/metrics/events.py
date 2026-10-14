"""本机事件日志：每行一个 JSON，只存在用户缓存目录，用于收益报告。"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from pathlib import Path

EVENTS_FILE = "events.jsonl"
MAX_BYTES = 20 * 1024 * 1024


def log_event(cache_dir: Path, event_type: str, **fields) -> None:
    if os.environ.get("PMEM_NO_EVENTS"):
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / EVENTS_FILE
        if path.exists() and path.stat().st_size > MAX_BYTES:
            path.replace(path.with_suffix(".old.jsonl"))
        record = {"ts": round(time.time(), 3), "type": event_type, **{k: v for k, v in fields.items() if v is not None}}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


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
