"""按当前代码核对记忆：记忆写下（或上次核对）之后，关联代码是否改过、删了或找不到符号。

检索、记忆图谱、读代码摘要、改代码拦截和 Wiki 共用这一套判断。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from pmem.core.config import MEMORY_DIR

if TYPE_CHECKING:
    from pmem.core.entry import Entry
    from pmem.vcs.base import VCS

CHANGE_CACHE_SECONDS = 60.0
# MCP 服务是长驻进程，每次检索选中的记忆组合不同都会新增缓存项
MAX_CACHED = 512
STATE_CACHE_SECONDS = 600.0
ANCHOR_CACHE = "anchors.json"
SAME_WORK_DAYS = 7
STALE_LABEL = "需核实"
_DEF_KEYWORDS = r"(?:def|class|function|func|fn|struct|interface|enum|record)"
_NOT_DEF_PREFIX = re.compile(r"^\s*(?:return|if|else|while|for|foreach|switch|case|await|new|throw|yield)\b")


def _definition_line(lines: list[str], name: str) -> int | None:
    """符号的定义行：先找带定义关键字的行，再找“名字(参数)”后面紧跟方法体的行（C#/Java/TS 方法）。"""
    word = re.escape(name)
    keyword = re.compile(rf"\b{_DEF_KEYWORDS}\s+{word}\b")
    for i, line in enumerate(lines):
        if keyword.search(line):
            return i
    call = re.compile(rf"\b{word}\s*(?:<[^>]*>)?\s*\(")
    for i, line in enumerate(lines):
        if not call.search(line) or _NOT_DEF_PREFIX.match(line) or line.rstrip().endswith(";"):
            continue
        tail = line[call.search(line).end():] + "".join(lines[i + 1:i + 3])
        if "{" in tail or "=>" in tail:
            return i
    return None


def _member(symbol: str) -> str:
    """“类名.成员”“类名::成员”取成员名。"""
    return re.split(r"\.|::", symbol.strip())[-1]


def symbol_block(text: str, symbol: str) -> str | None:
    """文件里某个符号（函数、类、方法）的完整代码块，找不到返回 None。“类名.成员”按成员找。"""
    name = _member(symbol)
    if not name:
        return None
    lines = [line.rstrip() for line in text.splitlines()]
    start = _definition_line(lines, name)
    if start is None:
        return None
    head = lines[start]
    indent = len(head) - len(head.lstrip())
    if re.match(r"\s*(?:async\s+)?(?:def|class)\b", head):
        # 签名可能跨多行：括号配平且以冒号结尾的那一行之后才是函数体
        end, balance = start, 0
        while end < len(lines):
            balance += lines[end].count("(") - lines[end].count(")")
            if balance <= 0 and lines[end].endswith(":"):
                break
            end += 1
        end += 1
        while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent):
            end += 1
        return "\n".join(lines[start:end]).rstrip()
    depth, opened = 0, False
    for end in range(start, len(lines)):
        for char in lines[end]:
            if char == "{":
                depth, opened = depth + 1, True
            elif char == "}":
                depth -= 1
        if opened and depth <= 0:
            return "\n".join(lines[start:end + 1])
        if not opened and lines[end].rstrip().endswith(";"):
            break
    return None


class AnchorChecker:
    """cache_path 给出时，核对结果跨进程缓存：钩子、命令行、Wiki 各自是新进程，每次都重跑 git 太慢。

    缓存随工作区状态整体失效（当前提交、今天日期、记忆目录以外的未提交文件及其修改时间），
    单条记忆再按 id、写入日、核对日和锚点命中；不在 Git 下（取不到未提交文件）时不缓存。
    """

    def __init__(self, root: Path, vcs: VCS, cache_path: Path | None = None):
        self.root = root
        self.vcs = vcs
        self.cache_path = cache_path
        self._changes: dict[tuple, tuple[float, dict[str, str]]] = {}
        self._old_texts: dict[tuple[str, str], str | None] = {}
        self._state: tuple[float, str | None] | None = None

    def _changed_after(self, files: list[str], since: str) -> dict[str, str]:
        key = (tuple(files), since)
        cached = self._changes.get(key)
        if cached and time.monotonic() - cached[0] < CHANGE_CACHE_SECONDS:
            return cached[1]
        try:
            found = self.vcs.changed_after(files, since)
        except Exception:  # noqa: BLE001
            found = {}
        if len(self._changes) >= MAX_CACHED:
            self._changes.clear()
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

    def _symbol_changed(self, rel: str, symbol: str, baseline: str, current: str) -> bool | None:
        """符号所在代码块与基准日时相比是否改过；取不到旧版本或代码块时返回 None（只能按文件判断）。"""
        now = symbol_block(current, symbol)
        if now is None:
            return None
        key = (rel, baseline)
        if key not in self._old_texts:
            if len(self._old_texts) >= MAX_CACHED:
                self._old_texts.clear()
            self._old_texts[key] = self.vcs.file_at(rel, baseline)
        old = self._old_texts[key]
        return None if old is None else symbol_block(old, symbol) != now

    def _worktree_state(self) -> str | None:
        if self._state and time.monotonic() - self._state[0] < CHANGE_CACHE_SECONDS:
            return self._state[1]
        state = None
        try:
            # 指纹每次核对都要算，列未提交文件慢的版本库（SVN）不缓存，照旧只核对选中的锚点
            dirty = self.vcs.dirty_files() if self.vcs.cheap_dirty_files else None
            if dirty is not None:
                parts = [self.vcs.revision(), date.today().isoformat()]
                for rel in sorted(p for p in dirty if not p.startswith(f"{MEMORY_DIR}/")):
                    try:
                        stat = (self.root / rel).stat()
                        parts.append(f"{rel}:{stat.st_mtime_ns}:{stat.st_size}")
                    except OSError:
                        parts.append(f"{rel}:-")
                state = hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
        except Exception:  # noqa: BLE001
            state = None
        self._state = (time.monotonic(), state)
        return state

    def _load_cache(self, state: str) -> dict[str, list[str]]:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        fresh = data.get("state") == state and time.time() - data.get("time", 0) < STATE_CACHE_SECONDS
        return data.get("results", {}) if fresh else {}

    def _save_cache(self, state: str, results: dict[str, list[str]]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_path.with_name(f"{self.cache_path.name}.{os.getpid()}.tmp")
            tmp.write_text(json.dumps({"state": state, "time": time.time(), "results": results}, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, self.cache_path)
        except OSError:
            pass

    def check(self, entries: list[Entry], files: dict[str, Path]) -> dict[str, list[str]]:
        """id → 问题列表（文件已删除、符号找不到、某天改过）；files 是记忆 id → 记忆文件路径。

        锚点带符号（文件#函数）时只看这个函数：文件改过但该函数与基准日时一致，不算过期。
        """
        state = self._worktree_state() if self.cache_path and entries else None
        if state is None:
            return self._check(entries, files)
        cached = self._load_cache(state)
        keys = {e.id: "|".join((e.id, e.note_date, e.checked_date, *e.anchors)) for e in entries}
        missing = [e for e in entries if keys[e.id] not in cached]
        if missing:
            found = self._check(missing, files)
            cached.update({keys[e.id]: found.get(e.id, []) for e in missing})
            self._save_cache(state, cached)
        return {e.id: cached[keys[e.id]] for e in entries if cached[keys[e.id]]}

    def _check(self, entries: list[Entry], files: dict[str, Path]) -> dict[str, list[str]]:
        texts: dict[str, str | None] = {}
        problems: dict[str, list[str]] = {}
        alive: dict[str, list[tuple[Entry, str]]] = {}
        for entry in entries:
            for anchor in entry.anchors:
                rel, _, symbol = anchor.partition("#")
                rel = rel.replace("\\", "/")
                if rel not in texts:
                    path = self.root / rel
                    texts[rel] = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else None
                if texts[rel] is None:
                    _add(problems, entry.id, f"{rel} 已不存在")
                elif symbol and _member(symbol) not in texts[rel]:
                    _add(problems, entry.id, f"{rel} 中找不到 {symbol}")
                else:
                    alive.setdefault(rel, []).append((entry, symbol))
        if alive:
            baselines = self._baselines([e for group in alive.values() for e, _ in group], files)
            since = min(baselines.values())
            for rel, day in self._changed_after(sorted(alive), since).items():
                for entry, symbol in alive.get(rel, []):
                    base = baselines[entry.id]
                    if day <= base:
                        continue
                    changed = self._symbol_changed(rel, symbol, base, texts[rel] or "") if symbol else None
                    if changed is None:
                        _add(problems, entry.id, f"{rel} 于 {day} 改过")
                    elif changed:
                        _add(problems, entry.id, f"{rel} 中 {symbol} 在 {base} 之后改过")
        return problems


def _add(problems: dict[str, list[str]], entry_id: str, problem: str) -> None:
    found = problems.setdefault(entry_id, [])
    if problem not in found:
        found.append(problem)
