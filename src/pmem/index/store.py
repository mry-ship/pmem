from __future__ import annotations

import hashlib
import math
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from pmem.core.entry import Entry
from pmem.core.ids import ALPHABET
from pmem.index.embedder import Embedder
from pmem.index.synonyms import expansions
from pmem.index.tokenize import tokenize
from pmem.storage.files import FilesStorage

VISIBLE_STATUSES = ("active", "seed", "draft")
_BATCH_WINDOW_MS = 90 * 60 * 1000
SYNONYM_WEIGHT = 0.8
CHANGE_CACHE_SECONDS = 60.0
SAME_WORK_DAYS = 7


def entry_text(entry: Entry) -> str:
    """参与检索的文本：议题名 + 正文 + 常用叫法。"""
    text = f"{entry.entity} {entry.content}"
    return f"{text} {' '.join(entry.aliases)}" if entry.aliases else text


def ulid_ms(entry_id: str) -> int:
    value = 0
    for char in entry_id[:10].upper():
        index = ALPHABET.find(char)
        if index < 0:
            return 0
        value = value * 32 + index
    return value


@dataclass
class Indexed:
    entry: Entry
    path: Path
    stamp: tuple[int, int]
    digest: str
    tokens: Counter
    length: int


@dataclass
class SearchResult:
    items: list[dict] = field(default_factory=list)
    fallback: str | None = None
    degraded: str | None = None
    warnings: list[str] = field(default_factory=list)
    expanded: list[str] = field(default_factory=list)


class VectorCache:
    """按 (嵌入器, 内容哈希) 缓存向量；内容不变就不重算。"""

    def __init__(self, path: Path | None):
        self._memory: dict[tuple[str, str], np.ndarray] = {}
        self._db: sqlite3.Connection | None = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS vectors (model TEXT, hash TEXT, data BLOB, PRIMARY KEY (model, hash))"
            )

    def get_many(self, model: str, digests: list[str]) -> dict[str, np.ndarray]:
        found = {d: self._memory[(model, d)] for d in digests if (model, d) in self._memory}
        missing = [d for d in digests if d not in found]
        if self._db is not None and missing:
            for start in range(0, len(missing), 500):
                chunk = missing[start : start + 500]
                marks = ",".join("?" * len(chunk))
                rows = self._db.execute(
                    f"SELECT hash, data FROM vectors WHERE model = ? AND hash IN ({marks})", (model, *chunk)
                )
                for digest, blob in rows:
                    vec = np.frombuffer(blob, dtype=np.float32)
                    self._memory[(model, digest)] = vec
                    found[digest] = vec
        return found

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def put_many(self, model: str, items: dict[str, np.ndarray]) -> None:
        for digest, vec in items.items():
            self._memory[(model, digest)] = vec
        if self._db is not None and items:
            self._db.executemany(
                "INSERT OR REPLACE INTO vectors (model, hash, data) VALUES (?, ?, ?)",
                [(model, d, v.astype(np.float32).tobytes()) for d, v in items.items()],
            )
            self._db.commit()


class MemoryIndex:
    """记忆检索：文件为准、内存索引、向量缓存在用户缓存目录，随时可重建。"""

    def __init__(
        self,
        storage: FilesStorage,
        cache_dir: Path | None = None,
        embedder: Embedder | None = None,
        embedder_problem: str | None = None,
        throttle_seconds: float = 10.0,
    ):
        self.storage = storage
        self.embedder = embedder
        self.embedder_problem = embedder_problem
        self.throttle_seconds = throttle_seconds
        self.vectors = VectorCache(cache_dir / "vectors.db" if cache_dir else None)
        self._items: dict[Path, Indexed] = {}
        self._last_refresh = -math.inf
        self.warnings: list[str] = []
        self.synonyms: list[list[str]] = []
        self.version = 0
        self._changes: dict[tuple, tuple[float, dict[str, str]]] = {}

    def close(self) -> None:
        self.vectors.close()

    # ---- 增量刷新 ----

    def refresh(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_refresh < self.throttle_seconds:
            return
        self._last_refresh = now
        seen: set[Path] = set()
        warnings: list[str] = []
        for path in self.storage.iter_files():
            seen.add(path)
            stat = path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            current = self._items.get(path)
            if current and current.stamp == stamp:
                continue
            try:
                raw = path.read_bytes()
                entry = Entry.from_markdown(raw.decode("utf-8-sig"))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"跳过无法解析的记忆文件 {path.name}：{exc}")
                self._items.pop(path, None)
                continue
            text = entry_text(entry)
            tokens = Counter(tokenize(text))
            digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
            self._items[path] = Indexed(entry, path, stamp, digest, tokens, sum(tokens.values()))
            self.version += 1
        for gone in set(self._items) - seen:
            del self._items[gone]
            self.version += 1
        self.warnings = warnings

    def entries(self) -> list[Entry]:
        self.refresh()
        return [item.entry for item in self._items.values()]

    def superseded(self, as_of: str | None = None) -> set[str]:
        """被替代的记忆 id；给出 as_of 时只算那天及之前写下的替代关系。"""
        hidden: set[str] = set()
        for item in self._items.values():
            if item.entry.status in VISIBLE_STATUSES and (as_of is None or item.entry.note_date <= as_of):
                hidden.update(item.entry.supersedes)
        return hidden

    def find(self, entry_id: str) -> Entry | None:
        self.refresh()
        return next((i.entry for i in self._items.values() if i.entry.id == entry_id), None)

    def module_stats(self) -> dict[str, dict]:
        self.refresh()
        hidden = self.superseded()
        stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "entities": Counter()})
        for item in self._items.values():
            entry = item.entry
            if entry.status not in VISIBLE_STATUSES or entry.id in hidden:
                continue
            stats[entry.module]["count"] += 1
            stats[entry.module]["entities"][entry.entity] += 1
        return {
            module: {"count": s["count"], "entities": [e for e, _ in s["entities"].most_common(10)]}
            for module, s in stats.items()
        }

    def warm(self) -> int:
        """重新扫描全部记忆文件并补齐向量，返回已有向量的条目数。"""
        self.refresh(force=True)
        items = list(self._items.values())
        if self.embedder is None or not items:
            return 0
        return len(self._vectors_for(items))

    # ---- 检索 ----

    def _vectors_for(self, items: list[Indexed]) -> dict[str, np.ndarray]:
        assert self.embedder is not None
        digests = list({i.digest for i in items})
        found = self.vectors.get_many(self.embedder.id, digests)
        missing = [i for i in items if i.digest not in found]
        if missing:
            unique = {i.digest: entry_text(i.entry) for i in missing}
            matrix = self.embedder.embed(list(unique.values()))
            fresh = dict(zip(unique.keys(), matrix, strict=True))
            self.vectors.put_many(self.embedder.id, fresh)
            found.update(fresh)
        return found

    @staticmethod
    def _bm25(items: list[Indexed], weights: dict[str, float]) -> list[float]:
        """weights：查询词 → 权重（原词 1，同义展开的词较低）。"""
        if not weights or not items:
            return [0.0] * len(items)
        n = len(items)
        avg_len = sum(i.length for i in items) / n or 1.0
        df = Counter(t for i in items for t in weights if t in i.tokens)
        scores = []
        for item in items:
            score = 0.0
            for token, weight in weights.items():
                tf = item.tokens.get(token, 0)
                if not tf:
                    continue
                idf = math.log(1 + (n - df[token] + 0.5) / (df[token] + 0.5))
                score += weight * idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * item.length / avg_len))
            scores.append(score)
        top = max(scores)
        return [s / top if top > 0 else 0.0 for s in scores]

    def _query_weights(self, query: str) -> tuple[dict[str, float], list[str]]:
        weights = {t: 1.0 for t in tokenize(query)}
        extra = expansions(query, self.synonyms)
        for term in extra:
            for token in tokenize(term):
                weights.setdefault(token, SYNONYM_WEIGHT)
        return weights, extra

    def _changed_after(self, files: list[str], since: str) -> dict[str, str]:
        key = (tuple(files), since)
        cached = self._changes.get(key)
        if cached and time.monotonic() - cached[0] < CHANGE_CACHE_SECONDS:
            return cached[1]
        try:
            found = self.storage.vcs.changed_after(files, since)
        except Exception:  # noqa: BLE001
            found = {}
        self._changes[key] = (time.monotonic(), found)
        return found

    def _baselines(self, entries: list[Entry]) -> dict[str, str]:
        """每条记忆的核对基准日：此日及之前的代码改动视为已被这条记忆考虑过。

        通常先写记忆、过一两天才连同代码一起提交，记忆自己那次修复的提交不能算“之后改过”。
        记忆文件写下后不久就提交了（或还是本地草稿），提交日（草稿取今天）之前的改动算作同一份工作；
        隔了很久才提交的（如从别的系统导入）仍以写入日为准。
        """
        today = date.today()
        paths = {i.entry.id: i.path for i in self._items.values()}
        rels: dict[str, str] = {}
        for entry in entries:
            path = paths.get(entry.id)
            if path is not None:
                try:
                    rels[entry.id] = path.relative_to(self.storage.root).as_posix()
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

    def check_anchors(self, entries: list[Entry]) -> dict[str, list[str]]:
        """记忆写下（或上次核对）之后关联代码的变化：id → 问题列表（文件已删除、符号找不到、某天改过）。"""
        root = self.storage.root
        texts: dict[str, str | None] = {}
        problems: dict[str, list[str]] = {}
        alive: dict[str, list[Entry]] = {}
        for entry in entries:
            for anchor in entry.anchors:
                rel, _, symbol = anchor.partition("#")
                rel = rel.replace("\\", "/")
                if rel not in texts:
                    path = root / rel
                    texts[rel] = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else None
                if texts[rel] is None:
                    problems.setdefault(entry.id, []).append(f"{rel} 已不存在")
                elif symbol and symbol not in texts[rel]:
                    problems.setdefault(entry.id, []).append(f"{rel} 中找不到 {symbol}")
                else:
                    alive.setdefault(rel, []).append(entry)
        if alive:
            baselines = self._baselines([e for group in alive.values() for e in group])
            since = min(baselines.values())
            for rel, day in self._changed_after(sorted(alive), since).items():
                for entry in alive.get(rel, []):
                    if day > baselines[entry.id]:
                        problems.setdefault(entry.id, []).append(f"{rel} 于 {day} 改过")
        return problems

    def search(
        self,
        module: str | None,
        entity: str | None = None,
        query: str | None = None,
        limit: int = 5,
        max_per_batch: int = 2,
        half_life_days: float = 90,
        today: date | None = None,
        as_of: str | None = None,
        verify: bool = True,
    ) -> SearchResult:
        self.refresh()
        result = SearchResult(warnings=list(self.warnings))
        hidden = self.superseded(as_of)
        pool = [
            i
            for i in self._items.values()
            if i.entry.status in VISIBLE_STATUSES
            and i.entry.id not in hidden
            and (module is None or i.entry.module.lower() == module.lower())
            and (as_of is None or i.entry.note_date <= as_of)
        ]
        if entity:
            matched = [i for i in pool if i.entry.entity.lower() == entity.lower()]
            if matched:
                pool = matched
            elif pool:
                result.fallback = "module"
        if not pool:
            return result

        query = (query or "").strip()
        weights, extra = self._query_weights(query)
        result.expanded = extra
        keyword = self._bm25(pool, weights)
        semantic = [0.0] * len(pool)
        if query:
            if self.embedder is None:
                result.degraded = "keyword_only"
            else:
                try:
                    vectors = self._vectors_for(pool)
                    q = self.embedder.embed([" ".join([query, *extra])])[0]
                    semantic = [max(0.0, float(np.dot(vectors[i.digest], q))) for i in pool]
                except Exception as exc:  # noqa: BLE001
                    result.degraded = "keyword_only"
                    result.warnings.append(f"语义检索不可用，已退化为关键词检索：{exc}")

        today = date.fromisoformat(as_of) if as_of else (today or date.today())
        scored = []
        for item, kw, vec in zip(pool, keyword, semantic, strict=True):
            entry = item.entry
            rel = kw if result.degraded or not query else 0.6 * vec + 0.4 * kw
            bonus = 0.05 if entry.kind in ("exclusion", "correction") else 0.0
            if entity and entry.entity.lower() == entity.lower():
                bonus += 0.15
            try:
                checked = entry.note_date if as_of else entry.checked_date
                age = max(0, (today - date.fromisoformat(checked)).days)
            except ValueError:
                age = 0
            recency = 0.5 ** (age / half_life_days)
            scored.append(((rel + bonus) * (0.7 + 0.3 * recency), ulid_ms(entry.id), item))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

        per_batch: Counter = Counter()
        chosen: list[Entry] = []
        for _score, created, item in scored:
            entry = item.entry
            batch = entry.source_conversation or f"{entry.author}|{entry.module}|{created // _BATCH_WINDOW_MS}"
            if per_batch[batch] >= max_per_batch:
                continue
            per_batch[batch] += 1
            chosen.append(entry)
            if len(chosen) >= limit:
                break

        # 回看历史时代码早已变化，核对没有意义
        problems = self.check_anchors(chosen) if verify and not as_of else {}
        for entry in chosen:
            row = {
                "id": entry.id,
                "entity": entry.entity,
                "kind": entry.kind,
                "date": entry.note_date,
                "author": entry.author,
                "stale": entry.id in problems,
                "content": entry.content,
            }
            if module is None:
                row = {"module": entry.module, **row}
            if entry.id in problems:
                row["check"] = problems[entry.id]
            if entry.verified:
                row["verified"] = entry.verified
            if entry.status != "active":
                row["status"] = entry.status
            result.items.append(row)
        return result
