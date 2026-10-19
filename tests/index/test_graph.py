from pmem.core.entry import Entry
from pmem.core.registry import ModuleRegistry
from pmem.index.graph import MemoryGraph, digest

REGISTRY = ModuleRegistry({
    "modules": {
        "gameplay.Jigsaw": {"paths": ["src/Jigsaw/**"], "aliases": ["拼图"]},
        "system.AdChase": {"paths": ["src/Ads/**"], "aliases": ["追广告"]},
        "economy.Shop": {"paths": ["src/Shop/**"]},
    }
})


def entry(eid: str, module: str, entity: str, content: str, day: str, **kw) -> Entry:
    return Entry(id=eid, module=module, entity=entity, kind=kw.pop("kind", "conclusion"), content=content,
                 note_date=day, author="a", **kw)


def test_timeline_shows_who_replaced_whom_and_when():
    graph = MemoryGraph([
        entry("A1", "gameplay.Jigsaw", "Reward", "关卡结束发奖励", "2026-09-01"),
        entry("A2", "gameplay.Jigsaw", "reward", "改为领取时发奖励", "2026-10-01", supersedes=["A1"]),
        entry("A3", "gameplay.Jigsaw", "Config", "碎片数量", "2026-10-02"),
    ], REGISTRY)
    timeline = graph.timeline("gameplay.Jigsaw", "Reward")
    assert [r["id"] for r in timeline] == ["A1", "A2"]
    assert timeline[0]["superseded_by"] == "A2" and timeline[0]["until"] == "2026-10-01"
    assert timeline[1]["replaces"] == ["A1"] and "superseded_by" not in timeline[1]
    topics = {t["entity"]: t for t in graph.topics("gameplay.Jigsaw")}
    assert topics["reward"]["current"] == 1 and topics["reward"]["superseded"] == 1
    assert [r["id"] for r in topics["reward"]["latest"]] == ["A2"]
    assert topics["reward"]["latest"][0]["preview"] == "改为领取时发奖励"


def test_digest_prefers_exclusions_and_caps_each_topic():
    entries = [
        entry("C1", "gameplay.Jigsaw", "Reward", "结论一", "2026-10-03"),
        entry("C2", "gameplay.Jigsaw", "Reward", "结论二", "2026-10-02"),
        entry("C3", "gameplay.Jigsaw", "Reward", "结论三", "2026-10-01"),
        entry("E1", "gameplay.Jigsaw", "Ads", "不要在客户端去重", "2026-09-01", kind="exclusion"),
        entry("O1", "gameplay.Jigsaw", "Ads", "旧排除项", "2026-08-01", kind="exclusion"),
        entry("O2", "gameplay.Jigsaw", "Ads", "更正", "2026-08-02", kind="correction", supersedes=["O1"]),
    ]
    assert [e.id for e in digest(entries)] == ["E1", "O2", "C1", "C2"]
    assert [e.id for e in digest(entries, limit=2)] == ["E1", "O2"]


def test_related_modules_via_shared_code_and_mentions():
    graph = MemoryGraph([
        entry("J1", "gameplay.Jigsaw", "Reward", "拼图奖励翻倍走追广告的激励视频", "2026-10-01",
              anchors=["src/Jigsaw/Reward.cs", "src/Ads/RewardedAd.cs#Show"]),
        entry("S1", "economy.Shop", "Price", "商店价格与拼图奖励无关", "2026-10-01", anchors=["src/Jigsaw/Reward.cs"]),
        entry("X1", "economy.Shop", "Old", "已被替代的旧结论提到 AdChase", "2026-09-01"),
        entry("X2", "economy.Shop", "Old", "新结论", "2026-10-01", supersedes=["X1"]),
    ], REGISTRY)
    related = {r["module"]: r for r in graph.related("gameplay.Jigsaw")}
    assert set(related) == {"system.AdChase", "economy.Shop"}
    assert "共享代码" in related["system.AdChase"]["via"] and "正文提及" in related["system.AdChase"]["via"]
    assert related["economy.Shop"]["files"] == ["src/Jigsaw/Reward.cs"]
    shop = {r["module"] for r in graph.related("economy.Shop")}
    assert "system.AdChase" not in shop


def test_shared_code_counts_files_not_memory_pairs():
    hub = [entry(f"G{i}", "gameplay.Jigsaw", f"T{i}", "拼图结论", "2026-10-01", anchors=["src/Jigsaw/Hub.cs"])
           for i in range(10)]
    graph = MemoryGraph([
        *hub,
        entry("S1", "economy.Shop", "Price", "商店结论", "2026-10-01", anchors=["src/Jigsaw/Hub.cs"]),
        entry("A1", "system.AdChase", "Show", "广告结论", "2026-10-01",
              anchors=["src/Jigsaw/Hub.cs", "src/Jigsaw/Other.cs"]),
    ], REGISTRY)
    related = graph.related("gameplay.Jigsaw")
    assert [(r["module"], r["via"]) for r in related] == [
        ("system.AdChase", "共享代码 2 个文件"), ("economy.Shop", "共享代码 1 个文件")]
