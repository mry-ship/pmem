"""检索评测：对比不同嵌入后端在评测集上的前 1 / 前 3 命中率与耗时。

用法：uv run --extra embed python scripts/eval_retrieval.py [后端 ...]
后端写法：keyword、hash、onnx:<模型>、ollama:<模型>
"""
from __future__ import annotations

import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import yaml

from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.index.embedder import HashEmbedder, OllamaEmbedder, OnnxEmbedder
from pmem.index.store import MemoryIndex
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

DATASET = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eval" / "retrieval.yaml"
DEFAULT_BACKENDS = [
    "keyword",
    "onnx:BAAI/bge-small-zh-v1.5",
    "onnx:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "ollama:nomic-embed-text",
]


def build_embedder(spec: str, cache: Path):
    if spec == "keyword":
        return None
    if spec == "hash":
        return HashEmbedder()
    kind, _, model = spec.partition(":")
    if kind == "onnx":
        return OnnxEmbedder(model, cache_dir=cache / "models")
    if kind == "ollama":
        return OllamaEmbedder(model)
    raise ValueError(spec)


def evaluate(spec: str, data: dict, model_cache: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        storage = FilesStorage(root, detect_vcs(root, "none"))
        keys: dict[str, str] = {}
        for m in data["memories"]:
            entry = Entry(
                id=new_ulid(), module=m["module"], entity=m["entity"], kind=m.get("kind", "conclusion"),
                content=m["content"], note_date="2026-10-01", author=f"a{len(keys)}",
            )
            storage.write(entry)
            keys[entry.id] = m["key"]
        started = time.perf_counter()
        embedder = build_embedder(spec, model_cache)
        index = MemoryIndex(storage, cache_dir=root / "cache", embedder=embedder, throttle_seconds=0)
        load_s = time.perf_counter() - started
        top1 = top3 = 0
        misses = []
        started = time.perf_counter()
        for case in data["queries"]:
            result = index.search(module=None, query=case["q"], limit=3, max_per_batch=3, today=date(2026, 10, 14))
            got = [keys[item["id"]] for item in result.items]
            top1 += bool(got) and got[0] == case["expect"]
            top3 += case["expect"] in got
            if not got or got[0] != case["expect"]:
                misses.append(f"{case['q']}→{got[:1]}")
        query_s = time.perf_counter() - started
        index.close()
        n = len(data["queries"])
        return (
            f"{spec:<70} top1={top1}/{n} top3={top3}/{n} 加载={load_s:.1f}s 查询总耗时={query_s:.1f}s\n"
            f"    未命中第一：{'; '.join(misses)}"
        )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = yaml.safe_load(DATASET.read_text(encoding="utf-8"))
    model_cache = Path(tempfile.gettempdir()) / "pmem-eval-cache"
    for spec in sys.argv[1:] or DEFAULT_BACKENDS:
        try:
            print(evaluate(spec, data, model_cache), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"{spec:<70} 失败：{exc}", flush=True)


if __name__ == "__main__":
    main()
