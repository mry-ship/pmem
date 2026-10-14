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

from pmem.core.entry import Entry
from pmem.core.ids import ALPHABET
from pmem.index.embedder import Embedder
from pmem.index.tokenize import tokenize
from pmem.storage.files import FilesStorage

VISIBLE_STATUSES = ("active", "seed", "draft")
_BATCH_WINDOW_MS = 90 * 60 * 1000


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
            text = f"{entry.entity} {entry.content}"
            tokens = Counter(tokenize(text))
            digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
            self._items[path] = Indexed(entry, path, stamp, digest, tokens, sum(tokens.values()))
        for gone in set(self._items) - seen:
            del self._items[gone]
        self.warnings = warnings

    def entries(self) -> list[Entry]:
        self.refresh()
        return [item.entry for item in self._items.values()]

    def superseded(self) -> set[str]:
        hidden: set[str] = set()
        for item in self._items.values():
            if item.entry.status in VISIBLE_STATUSES:
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
            unique = {i.digest: f"{i.entry.entity} {i.entry.content}" for i in missing}
            matrix = self.embedder.embed(list(unique.values()))
            fresh = dict(zip(unique.keys(), matrix, strict=True))
            self.vectors.put_many(self.embedder.id, fresh)
            found.update(fresh)
        return found

    @staticmethod
    def _bm25(items: list[Indexed], query_tokens: list[str]) -> list[float]:
        if not query_tokens or not items:
            return [0.0] * len(items)
        n = len(items)
        avg_len = sum(i.length for i in items) / n or 1.0
        df = Counter(t for i in items for t in set(query_tokens) if t in i.tokens)
        scores = []
        for item in items:
            score = 0.0
            for token in set(query_tokens):
                tf = item.tokens.get(token, 0)
                if not tf:
                    continue
                idf = math.log(1 + (n - df[token] + 0.5) / (df[token] + 0.5))
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * item.length / avg_len))
            scores.append(score)
        top = max(scores)
        return [s / top if top > 0 else 0.0 for s in scores]

    def _anchor_stale(self, anchors: list[str], cache: dict[str, str | None]) -> bool:
        root = self.storage.root
        for anchor in anchors:
            rel, _, symbol = anchor.partition("#")
            if rel not in cache:
                path = root / rel.replace("\\", "/")
                cache[rel] = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else None
            text = cache[rel]
            if text is None or (symbol and symbol not in text):
                return True
        return False

    def search(
        self,
        module: str | None,
        entity: str | None = None,
        query: str | None = None,
        limit: int = 5,
        max_per_batch: int = 2,
        half_life_days: float = 90,
        today: date | None = None,
    ) -> SearchResult:
        self.refresh()
        result = SearchResult(warnings=list(self.warnings))
        hidden = self.superseded()
        pool = [
            i
            for i in self._items.values()
            if i.entry.status in VISIBLE_STATUSES
            and i.entry.id not in hidden
            and (module is None or i.entry.module.lower() == module.lower())
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
        keyword = self._bm25(pool, tokenize(query))
        semantic = [0.0] * len(pool)
        if query:
            if self.embedder is None:
                result.degraded = "keyword_only"
            else:
                try:
                    vectors = self._vectors_for(pool)
                    q = self.embedder.embed([query])[0]
                    semantic = [max(0.0, float(np.dot(vectors[i.digest], q))) for i in pool]
                except Exception as exc:  # noqa: BLE001
                    result.degraded = "keyword_only"
                    result.warnings.append(f"语义检索不可用，已退化为关键词检索：{exc}")

        today = today or date.today()
        scored = []
        for item, kw, vec in zip(pool, keyword, semantic, strict=True):
            entry = item.entry
            rel = kw if result.degraded or not query else 0.6 * vec + 0.4 * kw
            bonus = 0.05 if entry.kind in ("exclusion", "correction") else 0.0
            if entity and entry.entity.lower() == entity.lower():
                bonus += 0.15
            try:
                age = max(0, (today - date.fromisoformat(entry.note_date)).days)
            except ValueError:
                age = 0
            recency = 0.5 ** (age / half_life_days)
            scored.append(((rel + bonus) * (0.7 + 0.3 * recency), ulid_ms(entry.id), item))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

        per_batch: Counter = Counter()
        anchor_cache: dict[str, str | None] = {}
        for score, created, item in scored:
            entry = item.entry
            batch = entry.source_conversation or f"{entry.author}|{entry.module}|{created // _BATCH_WINDOW_MS}"
            if per_batch[batch] >= max_per_batch:
                continue
            per_batch[batch] += 1
            row = {
                "id": entry.id,
                "entity": entry.entity,
                "kind": entry.kind,
                "date": entry.note_date,
                "author": entry.author,
                "stale": self._anchor_stale(entry.anchors, anchor_cache),
                "content": entry.content,
            }
            if module is None:
                row = {"module": entry.module, **row}
            if entry.status != "active":
                row["status"] = entry.status
            result.items.append(row)
            if len(result.items) >= limit:
                break
        return result
