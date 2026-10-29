import os
import subprocess
from datetime import date, datetime, timedelta

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


def test_vector_db_is_opened_only_when_vectors_are_used(storage, tmp_path):
    add(storage, "奖励重复发放的根因是领取按钮没有防连点")
    db = tmp_path / "cache" / "vectors.db"
    keyword = make_index(storage, tmp_path, embedder=None)
    assert keyword.search(module="gameplay.Jigsaw", query="奖励", today=TODAY).items
    keyword.close()
    assert not db.exists()

    semantic = make_index(storage, tmp_path)
    assert semantic.search(module="gameplay.Jigsaw", query="奖励", today=TODAY).items
    semantic.close()
    assert db.exists()


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
    assert len(result.items) == 5
    assert other.id in ids(result)[:3]


def test_same_author_batch_is_a_90_minute_window_not_a_fixed_bucket():
    from pmem.index.store import _BATCH_WINDOW_MS, _spread_batches

    edge = _BATCH_WINDOW_MS * 1000
    entries = [Entry(id=new_ulid(), module="m.A", entity="E", kind="conclusion", content="x",
                     note_date="2026-10-14", author="alice") for _ in range(3)]
    other = Entry(id=new_ulid(), module="m.A", entity="E", kind="conclusion", content="x", note_date="2026-10-14",
                  author="bob")
    ranked = [(1.0, edge - 60_000, entries[0]), (0.9, edge + 60_000, entries[1]), (0.8, edge + 120_000, entries[2]),
              (0.1, edge, other)]
    chosen = _spread_batches(ranked, limit=10, max_per_batch=2)
    assert chosen == [entries[0], entries[1], other, entries[2]]


def test_batch_overflow_is_demoted_but_still_beats_unrelated_entries(storage, tmp_path):
    """超出同批名额的记忆只降到其他相关结果之后，不能整条丢掉、输给完全不相干的记忆。"""
    same = [add(storage, f"奖励重复发放的第 {i} 个原因", source_conversation="conv-1") for i in range(3)]
    unrelated = [add(storage, f"配置表字段说明 {i}", entity="Config", source_conversation=f"conv-{i + 2}")
                 for i in range(3)]
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励重复发放", today=TODAY)
    assert set(ids(result)[:3]) == {e.id for e in same}
    assert set(ids(result)[3:]) <= {e.id for e in unrelated}


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


def test_empty_query_prefers_pitfalls_and_caps_other_lessons(storage, tmp_path):
    """无关键词命中的模块速览：防错类排前，默认名额内结论最多占 2 条。"""
    excl = add(storage, "不要按采用率调检索排序，每人结果会不同", kind="exclusion",
               entity="Ranking", source_conversation="c-ex")
    conclusions = [
        add(storage, f"模块说明结论 {i}", entity=f"Note{i}", kind="conclusion",
            source_conversation=f"c-{i}")
        for i in range(6)
    ]
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", today=TODAY, limit=5)
    got = ids(result)
    assert got[0] == excl.id
    assert len(got) == 3
    assert set(got[1:]).issubset({e.id for e in conclusions})


def test_keyword_query_keeps_in_quota_order(storage, tmp_path):
    """有关键词命中时名额内保持原排序，不能把无关防错挤到命中前面。"""
    hit = add(storage, "奖励弹窗的关闭逻辑", kind="conclusion", entity="Popup")
    add(storage, "不要用时间排序", kind="exclusion", entity="Ranking", source_conversation="other")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", query="奖励弹窗", today=TODAY)
    assert ids(result)[0] == hit.id


def test_empty_query_high_limit_does_not_cap_other_lessons(storage, tmp_path):
    items = [add(storage, f"模块说明 {i}", entity=f"Note{i}", source_conversation=f"c-{i}") for i in range(6)]
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", today=TODAY, limit=10, max_per_batch=10)
    assert len(result.items) == 6
    assert set(ids(result)) == {e.id for e in items}


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


def _touch(path, day: str) -> None:
    stamp = datetime.fromisoformat(f"{day}T12:00:00").timestamp()
    os.utime(path, (stamp, stamp))


def test_stale_anchor_detection(storage, tmp_path):
    src = tmp_path / "src" / "Reward.cs"
    src.parent.mkdir()
    src.write_text("class Reward { void Grant() {} }", encoding="utf-8")
    _touch(src, "2026-10-01")
    add(storage, "有效锚点", anchors=["src/Reward.cs#Grant"], entity="A")
    add(storage, "符号不存在", anchors=["src/Reward.cs#Missing"], entity="B")
    add(storage, "文件不存在", anchors=["src/Gone.cs"], entity="C")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", today=TODAY, limit=10, max_per_batch=10)
    stale = {item["entity"]: item["stale"] for item in result.items}
    assert stale == {"A": False, "B": True, "C": True}
    checks = {item["entity"]: item.get("check") for item in result.items}
    assert checks["B"] == ["src/Reward.cs 中找不到 Missing"] and checks["C"] == ["src/Gone.cs 已不存在"]


def test_code_changed_after_memory_is_stale_until_confirmed(storage, tmp_path):
    src = tmp_path / "src" / "Reward.cs"
    src.parent.mkdir()
    src.write_text("class Reward { void Grant() {} }", encoding="utf-8")
    _touch(src, "2026-10-12")
    old = add(storage, "领取前先校验次数", anchors=["src/Reward.cs#Grant"], note_date="2026-10-05", entity="A")
    fresh = add(storage, "领取后刷新红点", anchors=["src/Reward.cs"], note_date="2026-10-12", entity="B")
    confirmed = add(storage, "奖励按配置发", anchors=["src/Reward.cs"], note_date="2026-10-05",
                    verified="2026-10-13", entity="C")
    result = make_index(storage, tmp_path).search(module="gameplay.Jigsaw", today=TODAY, limit=10, max_per_batch=10)
    rows = {item["id"]: item for item in result.items}
    assert rows[old.id]["stale"] and rows[old.id]["check"] == ["src/Reward.cs 于 2026-10-12 改过"]
    assert not rows[fresh.id]["stale"]
    assert not rows[confirmed.id]["stale"] and rows[confirmed.id]["verified"] == "2026-10-13"


def test_own_fix_commit_is_not_a_later_change(git_repo, tmp_path):
    def day(n: int) -> str:
        return (date.today() - timedelta(days=n)).isoformat()

    def commit(when: str, *files: str) -> None:
        env = {**os.environ, "GIT_AUTHOR_DATE": f"{when}T12:00:00", "GIT_COMMITTER_DATE": f"{when}T12:00:00"}
        subprocess.run(["git", "add", *files], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", when], cwd=git_repo, check=True, capture_output=True, env=env)

    def edit(name: str, text: str) -> str:
        path = git_repo / "src" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return f"src/{name}"

    store = FilesStorage(git_repo, detect_vcs(git_repo))
    files = [edit(n, "v1") for n in ("Own.cs", "Import.cs", "Later.cs", "Draft.cs")]
    commit(day(90), *files)
    later = store.write(Entry(id=new_ulid(), module="m.A", entity="Later", kind="conclusion", content="后来又改",
                              note_date=day(20), author="a", anchors=["src/Later.cs"]))
    commit(day(19), str(later.path))
    own = store.write(Entry(id=new_ulid(), module="m.A", entity="Own", kind="conclusion", content="修复本身",
                            note_date=day(3), author="a", anchors=["src/Own.cs"]))
    imported = store.write(Entry(id=new_ulid(), module="m.A", entity="Import", kind="conclusion", content="导入",
                                 note_date=day(60), author="a", anchors=["src/Import.cs"]))
    commit(day(2), edit("Own.cs", "v2"), str(own.path), edit("Import.cs", "v2"), edit("Later.cs", "v2"))
    commit(day(1), str(imported.path))
    draft = store.write(Entry(id=new_ulid(), module="m.A", entity="Draft", kind="conclusion", content="本地草稿",
                              note_date=day(1), author="a", anchors=["src/Draft.cs"]))
    edit("Draft.cs", "v2")

    index = MemoryIndex(store, throttle_seconds=0)
    rows = {i["entity"]: i for i in index.search(module="m.A", limit=10, max_per_batch=10).items}
    assert not rows["Own"]["stale"] and not rows["Draft"]["stale"]
    assert rows["Import"]["check"] == [f"src/Import.cs 于 {day(2)} 改过"]
    assert rows["Later"]["check"] == [f"src/Later.cs 于 {day(2)} 改过"]
    assert draft.entry.id in {i["id"] for i in rows.values()}


def test_synonym_groups_expand_the_query(storage, tmp_path):
    crash = add(storage, "进入拼图时崩溃，原因是图集为空", entity="Loading")
    add(storage, "拼图奖励按配置发放", entity="Reward")
    index = make_index(storage, tmp_path, embedder=None)
    assert ids(index.search(module="gameplay.Jigsaw", query="闪退", today=TODAY))[0] != crash.id
    index.synonyms = [["闪退", "崩溃", "crash"]]
    result = index.search(module="gameplay.Jigsaw", query="闪退", today=TODAY)
    assert ids(result)[0] == crash.id and result.expanded == ["崩溃", "crash"]


def test_aliases_are_searchable(storage, tmp_path):
    target = add(storage, "进入拼图时崩溃，原因是图集为空", entity="Loading", aliases=["闪退"])
    add(storage, "拼图奖励按配置发放", entity="Reward")
    result = make_index(storage, tmp_path, embedder=None).search(module="gameplay.Jigsaw", query="闪退", today=TODAY)
    assert ids(result)[0] == target.id


def test_as_of_shows_what_was_valid_then(storage, tmp_path):
    first = add(storage, "奖励在关卡结束时发放", note_date="2026-09-01")
    second = add(storage, "奖励改为领取时发放，避免断线丢奖励", note_date="2026-10-01", supersedes=[first.id])
    index = make_index(storage, tmp_path)
    assert ids(index.search(module="gameplay.Jigsaw", today=TODAY)) == [second.id]
    assert ids(index.search(module="gameplay.Jigsaw", as_of="2026-09-15")) == [first.id]
    assert ids(index.search(module="gameplay.Jigsaw", as_of="2026-10-02")) == [second.id]


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
