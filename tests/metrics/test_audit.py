import time
from pathlib import Path

import pytest
import yaml

from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.core.registry import ModuleRegistry
from pmem.metrics.audit import (
    RECALL_MIN_LESSONS,
    RECALL_MIN_SEARCHES,
    promotion_hints,
    recall_audit,
    render_recall,
    render_unregistered,
)

MODULES = """
categories: { gameplay: {}, infra: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  infra.Common: { paths: [src/**] }
  gameplay.Old: { paths: [src/Old/**], status: deprecated }
candidates:
  gameplay.Cold: { paths: [src/Cold/**] }
"""
_clock = [int(time.time() * 1000)]


def _mk(module: str, kind: str = "conclusion", entity: str = "E", anchors: list[str] | None = None) -> Entry:
    _clock[0] += 1
    return Entry(id=new_ulid(_clock[0]), module=module, entity=entity, kind=kind, content="正文",
                 note_date="2026-10-20", author="a", anchors=anchors or [])


@pytest.fixture
def root(tmp_path) -> Path:
    for rel in ("src/Shop/Shop.cs", "src/Shop/Price.cs", "src/Pay/Pay.cs"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    return tmp_path


@pytest.fixture
def registry() -> ModuleRegistry:
    return ModuleRegistry(yaml.safe_load(MODULES))


def test_promotion_suggests_paths_and_current_owner(root, registry):
    entries = [_mk("economy.Shop", anchors=["src/Shop/Shop.cs#Buy", "src/Shop/Price.cs"]),
               _mk("economy.Shop", anchors=["src/Pay/Pay.cs", "src/Gone.cs"])]
    rows = [{"module": "economy.Shop", "memories": 2, "candidate": False, "similar": []}]
    promotion_hints(root, registry, entries, rows)
    assert rows[0]["paths"] == ["src/Shop/**", "src/Pay/Pay.cs"]
    assert rows[0]["owners"] == [("infra.Common", 3)] and rows[0]["anchored_files"] == 3
    text = render_unregistered(rows[0])
    assert "现在归 infra.Common 3 个" in text and "建议 paths: [src/Shop/**, src/Pay/Pay.cs]" in text


def test_promotion_without_anchors_and_for_candidates(root, registry):
    rows = [{"module": "economy.Shop", "memories": 1, "candidate": False, "similar": ["gameplay.Jigsaw"]},
            {"module": "gameplay.Cold", "memories": 1, "candidate": True, "similar": []}]
    promotion_hints(root, registry, [_mk("economy.Shop"), _mk("gameplay.Cold")], rows)
    assert "推断不出路径" in render_unregistered(rows[0]) and "相近：gameplay.Jigsaw" in render_unregistered(rows[0])
    assert "pmem sync --apply" in render_unregistered(rows[1])


def _searches(module: str, ids: list[str], n: int = RECALL_MIN_SEARCHES) -> list[dict]:
    return [{"type": "search", "ok": True, "module": module, "ids": ids} for _ in range(n)]


def test_recall_flags_module_whose_lessons_never_come_back(registry):
    lessons = [_mk("gameplay.Jigsaw", entity=f"T{i % 8}") for i in range(RECALL_MIN_LESSONS * 2)]
    features = [_mk("gameplay.Jigsaw", kind="feature") for _ in range(5)]
    rows = recall_audit(registry, lessons + features, _searches("gameplay.Jigsaw", [lessons[0].id, lessons[8].id]))
    assert len(rows) == 1
    row = rows[0]
    assert (row["lessons"], row["returned"], row["entities"]) == (RECALL_MIN_LESSONS * 2, 2, 8)
    assert "可考虑拆模块" in render_recall(row) and "T1（3 条）" in render_recall(row)


def test_recall_skips_small_samples_healthy_and_deprecated_modules(registry):
    lessons = [_mk("gameplay.Jigsaw") for _ in range(RECALL_MIN_LESSONS)]
    assert recall_audit(registry, lessons, _searches("gameplay.Jigsaw", [], RECALL_MIN_SEARCHES - 1)) == []
    assert recall_audit(registry, lessons[:-1], _searches("gameplay.Jigsaw", [])) == []
    healthy = _searches("gameplay.Jigsaw", [e.id for e in lessons[:3]])
    assert recall_audit(registry, lessons, healthy) == []
    old = [_mk("gameplay.Old") for _ in range(RECALL_MIN_LESSONS)]
    assert recall_audit(registry, old, _searches("gameplay.Old", [])) == []
