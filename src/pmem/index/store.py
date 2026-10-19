from __future__ import annotations

import hashlib
import math
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from pmem.core.entry import REPLACING_STATUSES, VISIBLE_STATUSES, Entry
from pmem.core.ids import ulid_ms
from pmem.index.anchors import ANCHOR_CACHE, AnchorChecker, anchor_affinity
from pmem.index.embedder import Embedder
from pmem.index.synonyms import expansions
from pmem.index.tokenize import tokenize
from pmem.storage.files import FilesStorage

BOOSTED_KINDS = ("exclusion", "correction")
# 按文件检索时锚点命中的加分。相关度在 0～1 之间：只给路径时它决定顺序，带了 query 时只起辅助作用
ANCHOR_BONUS = {2: 0.3, 1: 0.1, 0: 0.0}
_BATCH_WINDOW_MS = 90 * 60 * 1000
SYNONYM_WEIGHT = 0.8


def entry_text(entry: Entry) -> str:
    """参与检索的文本：议题名 + 正文 + 常用叫法。"""
    text = f"{entry.entity} {entry.content}"
    return f"{text} {' '.join(entry.aliases)}" if entry.aliases else text


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
    """按 (嵌入器, 内容哈希) 缓存向量；内容不变就不重算。
    数据库在第一次读写向量时才打开：只用关键词检索的进程（Hook、命令行）不必建 vectors.db、也不占它的写锁。"""

    def __init__(self, path: Path | None):
        self._memory: dict[tuple[str, str], np.ndarray] = {}
        self._path = path
        self._db: sqlite3.Connection | None = None

    def _conn(self) -> sqlite3.Connection | None:
        if self._db is None and self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(self._path), timeout=10, check_same_thread=False)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS vectors (model TEXT, hash TEXT, data BLOB, PRIMARY KEY (model, hash))"
            )
        return self._db

    def get_many(self, model: str, digests: list[str]) -> dict[str, np.ndarray]:
        found = {d: self._memory[(model, d)] for d in digests if (model, d) in self._memory}
        missing = [d for d in digests if d not in found]
        db = self._conn() if missing else None
        if db is not None:
            for start in range(0, len(missing), 500):
                chunk = missing[start : start + 500]
                marks = ",".join("?" * len(chunk))
                rows = db.execute(
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
        db = self._conn() if items else None
        if db is not None:
            db.executemany(
                "INSERT OR REPLACE INTO vectors (model, hash, data) VALUES (?, ?, ?)",
                [(model, d, v.astype(np.float32).tobytes()) for d, v in items.items()],
            )
            db.commit()


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
        self.checker = AnchorChecker(storage.root, storage.vcs, cache_dir / ANCHOR_CACHE if cache_dir else None)

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
            try:
                stat = path.stat()
            except OSError:
                # 列出之后被移走（migrate、切分支），按已删除处理
                continue
            seen.add(path)
            stamp = (stat.st_mtime_ns, stat.st_size)
            current = self._items.get(path)
            if current and current.stamp == stamp:
                continue
            try:
                raw = path.read_bytes()
                entry = Entry.from_markdown(raw.decode("utf-8-sig"))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"跳过无法解析的记忆文件 {path.name}：{exc}")
                if self._items.pop(path, None) is not None:
                    self.version += 1
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
            if item.entry.status in REPLACING_STATUSES and (as_of is None or item.entry.note_date <= as_of):
                hidden.update(item.entry.supersedes)
        return hidden

    def _visible_items(self, as_of: str | None = None) -> list[Indexed]:
        self.refresh()
        hidden = self.superseded(as_of)
        return [
            i for i in self._items.values()
            if i.entry.status_on(as_of) in VISIBLE_STATUSES
            and i.entry.id not in hidden
            and (as_of is None or i.entry.note_date <= as_of)
        ]

    def visible(self, as_of: str | None = None) -> list[Entry]:
        """检索得到的记忆：状态有效、没被替代；给出 as_of 时只看那天及之前写下的，那天之后才归档的仍算有效。"""
        return [i.entry for i in self._visible_items(as_of)]

    def find(self, entry_id: str) -> Entry | None:
        self.refresh()
        return next((i.entry for i in self._items.values() if i.entry.id == entry_id), None)

    def module_stats(self) -> dict[str, dict]:
        stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "entities": Counter()})
        for entry in self.visible():
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

    def check_anchors(self, entries: list[Entry]) -> dict[str, list[str]]:
        """记忆写下（或上次核对）之后关联代码的变化：id → 问题列表（文件已删除、符号找不到、某天改过）。"""
        return self.checker.check(entries, {i.entry.id: i.path for i in self._items.values()})

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
        semantic: bool = True,
        path: str | None = None,
    ) -> SearchResult:
        """排序 = (相关度 + 加分) × 时效；相关度 = 0.6 × 语义 + 0.4 × 关键词（无语义时只用关键词）。
        path 是要改的文件（项目相对路径）：锚点就是它的记忆加分，免得只按新旧排、被模块里别的方面挤掉。"""
        pool = [i for i in self._visible_items(as_of) if module is None or _same(i.entry.module, module)]
        result = SearchResult(warnings=list(self.warnings))
        if entity:
            matched = [i for i in pool if _same(i.entry.entity, entity)]
            if matched:
                pool = matched
            elif pool:
                result.fallback = "module"
        if not pool:
            return result

        query = (query or "").strip()
        weights, result.expanded = self._query_weights(query)
        relevance = self._relevance(pool, query, weights, result) if semantic else self._bm25(pool, weights)
        day = date.fromisoformat(as_of) if as_of else (today or date.today())
        ranked = sorted(
            (
                (_score(i.entry, rel + ANCHOR_BONUS[anchor_affinity(i.entry.anchors, path)], entity, day,
                        half_life_days, as_of), ulid_ms(i.entry.id), i.entry)
                for i, rel in zip(pool, relevance, strict=True)
            ),
            key=lambda t: (t[0], t[1]),
            reverse=True,
        )
        chosen = _spread_batches(ranked, limit, max_per_batch)
        # 回看历史时代码早已变化，核对没有意义
        problems = self.check_anchors(chosen) if verify and not as_of else {}
        result.items = [_row(e, problems.get(e.id), with_module=module is None) for e in chosen]
        return result

    def _relevance(self, pool: list[Indexed], query: str, weights: dict[str, float], result: SearchResult) -> list[float]:
        keyword = self._bm25(pool, weights)
        if not query:
            return keyword
        if self.embedder is None:
            result.degraded = "keyword_only"
            return keyword
        try:
            vectors = self._vectors_for(pool)
            q = self.embedder.embed([" ".join([query, *result.expanded])])[0]
            semantic = [max(0.0, float(np.dot(vectors[i.digest], q))) for i in pool]
        except Exception as exc:  # noqa: BLE001
            result.degraded = "keyword_only"
            result.warnings.append(f"语义检索不可用，已退化为关键词检索：{exc}")
            return keyword
        return [0.6 * vec + 0.4 * kw for vec, kw in zip(semantic, keyword, strict=True)]


def _same(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def _score(entry: Entry, relevance: float, entity: str | None, today: date, half_life_days: float,
           as_of: str | None) -> float:
    bonus = 0.05 if entry.kind in BOOSTED_KINDS else 0.0
    if entity and _same(entry.entity, entity):
        bonus += 0.15
    try:
        checked = entry.note_date if as_of else entry.checked_date
        age = max(0, (today - date.fromisoformat(checked)).days)
    except ValueError:
        age = 0
    recency = 0.5 ** (age / half_life_days)
    return (relevance + bonus) * (0.7 + 0.3 * recency)


def _spread_batches(ranked: list[tuple[float, int, Entry]], limit: int, max_per_batch: int) -> list[Entry]:
    """同一批（同一对话，或同一作者同一模块 90 分钟内）最多取 max_per_batch 条，免得碎片挤占名额。"""
    per_batch: Counter = Counter()
    chosen: list[Entry] = []
    for _score, created, entry in ranked:
        batch = entry.source_conversation or f"{entry.author}|{entry.module}|{created // _BATCH_WINDOW_MS}"
        if per_batch[batch] >= max_per_batch:
            continue
        per_batch[batch] += 1
        chosen.append(entry)
        if len(chosen) >= limit:
            break
    return chosen


def _row(entry: Entry, problems: list[str] | None, with_module: bool) -> dict:
    row = {
        "id": entry.id,
        "entity": entry.entity,
        "kind": entry.kind,
        "date": entry.note_date,
        "author": entry.author,
        "stale": problems is not None,
        "content": entry.content,
    }
    if with_module:
        row = {"module": entry.module, **row}
    if problems is not None:
        row["check"] = problems
    if entry.verified:
        row["verified"] = entry.verified
    if entry.status != "active":
        row["status"] = entry.status
    return row
