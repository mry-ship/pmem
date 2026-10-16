"""按当前代码核对记忆：记忆写下（或上次核对）之后，关联代码是否改过、删了或找不到符号。

检索、记忆图谱、读代码摘要、改代码拦截和 Wiki 共用这一套判断。
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from pmem.core.entry import Entry
from pmem.vcs.base import VCS

CHANGE_CACHE_SECONDS = 60.0
SAME_WORK_DAYS = 7
STALE_LABEL = "需核实"


class AnchorChecker:
    def __init__(self, root: Path, vcs: VCS):
        self.root = root
        self.vcs = vcs
        self._changes: dict[tuple, tuple[float, dict[str, str]]] = {}

    def _changed_after(self, files: list[str], since: str) -> dict[str, str]:
        key = (tuple(files), since)
        cached = self._changes.get(key)
        if cached and time.monotonic() - cached[0] < CHANGE_CACHE_SECONDS:
            return cached[1]
        try:
            found = self.vcs.changed_after(files, since)
        except Exception:  # noqa: BLE001
            found = {}
        self._changes[key] = (time.monotonic(), found)
        return found

    def _baselines(self, entries: list[Entry], files: dict[str, Path]) -> dict[str, str]:
        """每条记忆的核对基准日：此日及之前的代码改动视为已被这条记忆考虑过。

        通常先写记忆、过一两天才连同代码一起提交，记忆自己那次修复的提交不能算“之后改过”。
        记忆文件写下后不久就提交了（或还是本地草稿），提交日（草稿取今天）之前的改动算作同一份工作；
        隔了很久才提交的（如从别的系统导入）仍以写入日为准。
        """
        today = date.today()
        rels: dict[str, str] = {}
        for entry in entries:
            path = files.get(entry.id)
            if path is not None:
                try:
                    rels[entry.id] = path.relative_to(self.root).as_posix()
                except ValueError:
                    pass
        earliest = min((e.note_date for e in entries), default="")
        try:
            since = (date.fromisoformat(earliest) - timedelta(days=1)).isoformat()
        except ValueError:
            since = "1970-01-01"
        committed = self._changed_after(sorted(set(rels.values())), since) if rels else {}
        baselines: dict[str, str] = {}
        for entry in entries:
            base = entry.checked_date
            try:
                written = date.fromisoformat(entry.note_date)
            except ValueError:
                baselines[entry.id] = base
                continue
            day = committed.get(rels.get(entry.id, ""))
            if day is None and entry.id in rels:
                day = today.isoformat()
            if day and (date.fromisoformat(day) - written).days <= SAME_WORK_DAYS:
                base = max(base, day)
            baselines[entry.id] = base
        return baselines

    def check(self, entries: list[Entry], files: dict[str, Path]) -> dict[str, list[str]]:
        """id → 问题列表（文件已删除、符号找不到、某天改过）；files 是记忆 id → 记忆文件路径。"""
        texts: dict[str, str | None] = {}
        problems: dict[str, list[str]] = {}
        alive: dict[str, list[Entry]] = {}
        for entry in entries:
            for anchor in entry.anchors:
                rel, _, symbol = anchor.partition("#")
                rel = rel.replace("\\", "/")
                if rel not in texts:
                    path = self.root / rel
                    texts[rel] = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else None
                if texts[rel] is None:
                    problems.setdefault(entry.id, []).append(f"{rel} 已不存在")
                elif symbol and symbol not in texts[rel]:
                    problems.setdefault(entry.id, []).append(f"{rel} 中找不到 {symbol}")
                else:
                    alive.setdefault(rel, []).append(entry)
        if alive:
            baselines = self._baselines([e for group in alive.values() for e in group], files)
            since = min(baselines.values())
            for rel, day in self._changed_after(sorted(alive), since).items():
                for entry in alive.get(rel, []):
                    if day > baselines[entry.id]:
                        problems.setdefault(entry.id, []).append(f"{rel} 于 {day} 改过")
        return problems
