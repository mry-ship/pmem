import os
from datetime import date

import pytest

from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.index.embedder import HashEmbedder
from pmem.index.store import MemoryIndex
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

TODAY = date(2026, 10, 14)


class CountingEmbedder(HashEmbedder):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return super().embed(texts)


@pytest.fixture
def storage(tmp_path):
    return FilesStorage(tmp_path, detect_vcs(tmp_path, "none"))


def add(storage, content, module="gameplay.Jigsaw", entity="Reward", kind="conclusion", **kw):
    fields = {
        "id": new_ulid(),
        "module": module,
        "entity": entity,
        "kind": kind,
        "content": content,
        "note_date": "2026-10-14",
        "author": "alice",
    }
    fields.update(kw)
    return storage.write(Entry(**fields)).entry


def make_index(storage, tmp_path, embedder="hash"):
    emb = HashEmbedder() if embedder == "hash" else embedder
    return MemoryIndex(storage, cache_dir=tmp_path / "cache", embedder=emb, throttle_seconds=0)


def ids(result):
    return [item["id"] for item in result.items]


def test_relevant_entry_ranks_first(storage, tmp_path):
    add(storage, "拼图关卡加载慢，原因是图集未压缩", entity="Loading")
    target = add(storage, "奖励重复发放的根因是领取按钮没有防连点")
    add(storage, "拼图配置表字段 pieceCount 的含义", entity="Config")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励重复发放", today=TODAY)
    assert ids(result)[0] == target.id
    assert result.degraded is None


def test_other_modules_are_not_returned(storage, tmp_path):
    add(storage, "商店奖励重复发放", module="economy.Shop")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励重复", today=TODAY)
    assert result.items == []


def test_superseded_and_archived_are_hidden(storage, tmp_path):
    old = add(storage, "旧结论：奖励重复是网络重试导致")
    add(storage, "新结论：奖励重复是按钮连点导致", kind="correction", supersedes=[old.id])
    add(storage, "已归档的奖励说明", status="archived")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励重复", today=TODAY)
    assert old.id not in ids(result)
    assert len(result.items) == 1


def test_entity_filter_and_real_fallback(storage, tmp_path):
    reward = add(storage, "奖励发放走统一的 GrantReward 接口")
    add(storage, "配置表 pieceCount 表示碎片数量", entity="Config")
    index = make_index(storage, tmp_path)
    only = index.search(module="gameplay.Jigsaw", entity="Reward", today=TODAY)
    assert ids(only) == [reward.id]
    assert only.fallback is None
    fallback = index.search(module="gameplay.Jigsaw", entity="Balance", today=TODAY)
    assert len(fallback.items) == 2
    assert fallback.fallback == "module"


def test_entity_match_is_case_insensitive(storage, tmp_path):
    add(storage, "奖励发放走统一的 GrantReward 接口")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", entity="reward", today=TODAY)
    assert len(result.items) == 1


def test_same_batch_is_capped(storage, tmp_path):
    for i in range(4):
        add(storage, f"同一次对话里的第 {i} 条奖励结论", source_conversation="conv-1")
    other = add(storage, "另一次对话的奖励结论", source_conversation="conv-2")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励结论", today=TODAY)
    assert len(result.items) == 3
    assert other.id in ids(result)


def test_newer_entry_wins_on_equal_relevance(storage, tmp_path):
    old = add(storage, "奖励弹窗的关闭逻辑", note_date="2025-10-14")
    new = add(storage, "奖励弹窗的关闭逻辑", note_date="2026-10-10")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励弹窗", today=TODAY)
    assert ids(result) == [new.id, old.id]


def test_exclusion_gets_bonus(storage, tmp_path):
    plain = add(storage, "奖励弹窗的关闭逻辑")
    excl = add(storage, "奖励弹窗的关闭逻辑", kind="exclusion")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励弹窗", today=TODAY)
    assert ids(result) == [excl.id, plain.id]


def test_keyword_only_when_no_embedder(storage, tmp_path):
    target = add(storage, "奖励重复发放的根因是领取按钮没有防连点")
    add(storage, "拼图关卡加载慢，原因是图集未压缩", entity="Loading")
    result = make_index(storage, tmp_path, embedder=None).search(
        module="gameplay.Jigsaw", query="奖励重复", today=TODAY
    )
    assert ids(result)[0] == target.id
    assert result.degraded == "keyword_only"


def test_incremental_refresh_sees_add_modify_delete(storage, tmp_path):
    index = make_index(storage, tmp_path)
    first = add(storage, "第一条奖励结论")
    assert len(index.search(module="gameplay.Jigsaw", today=TODAY).items) == 1
    second = add(storage, "第二条奖励结论")
    assert len(index.search(module="gameplay.Jigsaw", today=TODAY).items) == 2
    path = storage.find_path(first.id)
    os.remove(path)
    assert ids(index.search(module="gameplay.Jigsaw", today=TODAY)) == [second.id]


def test_vectors_are_cached_across_instances(storage, tmp_path):
    add(storage, "第一条奖励结论")
    add(storage, "第二条奖励结论")
    emb = CountingEmbedder()
    make_index(storage, tmp_path, embedder=emb).search(module="gameplay.Jigsaw", query="奖励", today=TODAY)
    assert emb.calls == 3
    emb2 = CountingEmbedder()
    make_index(storage, tmp_path, embedder=emb2).search(module="gameplay.Jigsaw", query="奖励", today=TODAY)
    assert emb2.calls == 1


def test_stale_anchor_detection(storage, tmp_path):
    src = tmp_path / "src" / "Reward.cs"
    src.parent.mkdir()
    src.write_text("class Reward { void Grant() {} }", encoding="utf-8")
    add(storage, "有效锚点", anchors=["src/Reward.cs#Grant"], entity="A")
    add(storage, "符号不存在", anchors=["src/Reward.cs#Missing"], entity="B")
    add(storage, "文件不存在", anchors=["src/Gone.cs"], entity="C")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", today=TODAY, limit=10, max_per_batch=10)
    stale = {item["entity"]: item["stale"] for item in result.items}
    assert stale == {"A": False, "B": True, "C": True}


def test_global_search_without_module(storage, tmp_path):
    shop = add(storage, "商店刷新时间按服务器时区计算", module="economy.Shop", entity="Refresh")
    add(storage, "拼图碎片数量", entity="Config")
    result = make_index(storage, tmp_path).search(module=None, query="商店刷新时区", today=TODAY)
    assert ids(result)[0] == shop.id
    assert result.items[0]["module"] == "economy.Shop"


def test_module_counts(storage, tmp_path):
    add(storage, "一", entity="Reward")
    add(storage, "二", entity="Config")
    add(storage, "三", module="economy.Shop", entity="Price")
    counts = make_index(storage, tmp_path).module_stats()
    assert counts["gameplay.Jigsaw"]["count"] == 2
    assert set(counts["gameplay.Jigsaw"]["entities"]) == {"Reward", "Config"}
    assert counts["economy.Shop"]["count"] == 1
