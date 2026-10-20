"""按当前代码核对记忆：记忆写下（或上次核对）之后，关联代码是否改过、删了或找不到符号。

检索、记忆图谱、读代码摘要、改代码拦截和 Wiki 共用这一套判断。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import date, datetime
from datetime import time as dt_time
from pathlib import Path
from typing import TYPE_CHECKING

from pmem.core.config import MEMORY_DIR
from pmem.core.ids import ulid_ms

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


def _anchor_file(path: str) -> str:
    path = path.split("#", 1)[0].replace("\\", "/").lower()
    while path.startswith("./"):
        path = path[2:]
    return path


def anchor_affinity(anchors: list[str], rel: str | None) -> int:
    """记忆的锚点和某个文件的关系：2 锚点就是这个文件，1 在同一目录，0 无关。不区分大小写（Windows）。"""
    if not rel:
        return 0
    target = _anchor_file(rel)
    folder = target.rpartition("/")[0]
    best = 0
    for anchor in anchors:
        file = _anchor_file(anchor)
        if file == target:
            return 2
        if folder and file.rpartition("/")[0] == folder:
            best = 1
    return best


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
    """文件里某个符号（函数、类、方法）的完整代码块，找不到返回 None。
    “类名.成员”先找到类，再在类里找成员，免得落到别的类的同名方法（close、__init__）；找不到类时按成员找。"""
    parts = [p for p in re.split(r"\.|::", symbol.strip()) if p]
    if not parts:
        return None
    scope, scoped = text, False
    for owner in parts[:-1]:
        block = _block(scope, owner, scoped)
        if block is not None:
            scope, scoped = block, True
    return _block(scope, parts[-1], scoped)


def _block(text: str, name: str, inside: bool) -> str | None:
    """inside 为 True 时 text 是类的代码块，跳过类头那一行（构造函数与类同名）。"""
    lines = [line.rstrip() for line in text.splitlines()]
    offset = 1 if inside else 0
    start = _definition_line(lines[offset:], name)
    if start is None:
        return None
    start += offset
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
    单条记忆再按 id、写入日、核对时刻和锚点命中；不在 Git 下（取不到未提交文件）时不缓存。
    """

    def __init__(self, root: Path, vcs: VCS, cache_path: Path | None = None):
        self.root = root
        self.vcs = vcs
        self.cache_path = cache_path
        self._changes: dict[tuple, tuple[float, dict]] = {}
        self._old_texts: dict[tuple[str, float], str | None] = {}
        self._state: tuple[float, str | None] | None = None

    def _cached(self, kind: str, files: list[str], since: float, query) -> dict:
        key = (kind, tuple(files), since)
        cached = self._changes.get(key)
        if cached and time.monotonic() - cached[0] < CHANGE_CACHE_SECONDS:
            return cached[1]
        try:
            found = query(files, since)
        except Exception:  # noqa: BLE001
            found = {}
        if len(self._changes) >= MAX_CACHED:
            self._changes.clear()
        self._changes[key] = (time.monotonic(), found)
        return found

    def _baselines(self, entries: list[Entry], files: dict[str, Path]) -> dict[str, float]:
        """每条记忆的核对基准时刻（Unix 秒）：此刻及之前的代码改动视为已被这条记忆考虑过。

        基准先取写入或核对的时刻。写记忆、确认记忆时代码常还没提交，之后连同记忆一起提交，
        这次提交不能算“之后改过”：记忆文件在基准之后 SAME_WORK_DAYS 天内的第一次提交（从没提交过的草稿取现在）
        之前的改动算作同一份工作。只顺延到第一次提交：之后格式化、归档再提交记忆文件，不能把基准一路往后推。
        """
        rels: dict[str, str] = {}
        for entry in entries:
            path = files.get(entry.id)
            if path is not None:
                try:
                    rels[entry.id] = path.relative_to(self.root).as_posix()
                except ValueError:
                    pass
        checked = {e.id: checked_at(e) for e in entries}
        # 从写入前一天查起，拿到记忆文件的全部提交：区分“从没提交过的草稿”和“已提交、之后只是没再提交”
        since = min((written_at(e) for e in entries), default=0.0) - 86400
        commits = self._cached("commits", sorted(set(rels.values())), since, self.vcs.commit_times) if rels else {}
        now = time.time()
        baselines: dict[str, float] = {}
        for entry in entries:
            base = checked[entry.id]
            if entry.id in rels:
                times = commits.get(rels[entry.id], [])
                # 同一台机器写入和提交，时钟一致；留一分钟余量
                later = [t for t in times if t >= base - 60]
                first = later[0] if later else (None if times else now)
                if first is not None and first - base <= SAME_WORK_DAYS * 86400:
                    base = max(base, first)
            baselines[entry.id] = base
        return baselines

    def _symbol_problem(self, rel: str, symbol: str, baseline: float, current: str) -> str | None:
        """符号所在代码块与基准时相比：没变返回空串，有问题返回说明；取不到旧版本时返回 None（只能按文件判断）。"""
        key = (rel, baseline)
        if key not in self._old_texts:
            if len(self._old_texts) >= MAX_CACHED:
                self._old_texts.clear()
            self._old_texts[key] = self.vcs.file_before(rel, baseline)
        old_text = self._old_texts[key]
        if old_text is None:
            return None
        now, old = symbol_block(current, symbol), symbol_block(old_text, symbol)
        if now is None and old is None:
            return None
        if now is None:
            return f"{rel} 中找不到 {symbol}"
        return "" if now == old else f"{rel} 中 {symbol} 在 {_day(baseline)} 之后改过"

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
        keys = {e.id: "|".join((e.id, e.note_date, e.checked_date, e.verified_at or "", *e.anchors)) for e in entries}
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
            for rel, moment in self._cached("changes", sorted(alive), since, self.vcs.changed_since).items():
                for entry, symbol in alive.get(rel, []):
                    base = baselines[entry.id]
                    if moment <= base:
                        continue
                    problem = self._symbol_problem(rel, symbol, base, texts[rel] or "") if symbol else None
                    if problem is None:
                        _add(problems, entry.id, f"{rel} 于 {_day(moment)} 改过")
                    elif problem:
                        _add(problems, entry.id, problem)
        return problems


def _day(moment: float) -> str:
    # Windows 上 1970 年附近或超出范围的时间戳会抛 OSError / OverflowError / ValueError
    try:
        return datetime.fromtimestamp(max(moment, 86400)).date().isoformat()
    except (OSError, OverflowError, ValueError):
        return ""


def _end_of(day: str) -> float:
    return datetime.combine(date.fromisoformat(day), dt_time.max).timestamp()


def written_at(entry: Entry) -> float:
    """写入时刻：ULID 的生成时间与写入日对得上就用它（精确到毫秒）；
    对不上（导入的、手写 id 的）按写入日当天结束算；写入日也无效时取 0，之后的任何改动都算。"""
    try:
        end = _end_of(entry.note_date)
    except ValueError:
        return 0.0
    ms = ulid_ms(entry.id)
    return ms / 1000 if ms and _day(ms / 1000) == entry.note_date else end


def checked_at(entry: Entry) -> float:
    """最近一次确认成立的时刻：写入时刻与核对时刻取晚的；旧文件只有核对日期时按当天结束算。"""
    base = written_at(entry)
    verified = None
    if entry.verified_at:
        try:
            stamp = datetime.fromisoformat(entry.verified_at)
            verified = stamp.timestamp()
        except ValueError:
            verified = None
    if verified is None and entry.verified:
        try:
            verified = _end_of(entry.verified)
        except ValueError:
            verified = None
    return max(base, verified or 0.0)


def _add(problems: dict[str, list[str]], entry_id: str, problem: str) -> None:
    found = problems.setdefault(entry_id, [])
    if problem not in found:
        found.append(problem)
