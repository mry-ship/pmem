from __future__ import annotations

from pathlib import Path

from pmem.core.config import Config
from pmem.service import MemoryService

CACHE_FILES = ("vectors.db", "vectors.db-wal", "vectors.db-shm", "cites.json")


def run_reindex(root: Path) -> int:
    cache_dir = Config.load(root).cache_dir
    for name in CACHE_FILES:
        (cache_dir / name).unlink(missing_ok=True)
    service = MemoryService(root)
    try:
        index = service.index
        if index.embedder is not None:
            print("计算向量中（首次会下载语义模型）……")
        vectors = index.warm()
        count = len(index.entries())
        model = index.embedder.id if index.embedder is not None else None
        print(f"重建完成：记忆 {count} 条" + (f"，向量 {vectors} 条（{model}）" if model else "，未启用语义检索"))
        for warning in index.warnings + ([index.embedder_problem] if index.embedder_problem else []):
            print(f"  ! {warning}")
        return 1 if index.warnings else 0
    finally:
        service.close()
