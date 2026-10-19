from pathlib import Path

import pytest

from pmem.service import MemoryService

CONFIG = """
project: { name: demo }
vcs: none
embedding: { backend: none }
write: { content_min: 10, max_per_day_per_entity: 2 }
"""

MODULES = """
categories:
  activity: {}
  gameplay: {}
  economy: {}
  infra: {}
entities:
  Reward: [奖励, reward]
modules:
  gameplay.Jigsaw:
    paths: [src/Jigsaw/**]
    aliases: [Puzzle]
  economy.Shop:
    paths: [src/Shop/**]
  infra.Save:
    paths: [src/Save/**]
candidates:
  activity.Ladybug:
    paths: [src/Ladybug/**]
"""

LONG = "拼图奖励重复发放的根因是领取按钮没有防连点。"


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


@pytest.fixture
def svc(project) -> MemoryService:
    service = MemoryService(project)
    yield service
    service.close()


def record(svc, **kw):
    args = {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": LONG}
    args.update(kw)
    return svc.record(**args)


def test_record_then_search_by_module(svc, project):
    written = record(svc)
    assert written["ok"] is True
    assert (project / ".memory" / "entries" / "gameplay.Jigsaw" / f"{written['id']}.md").exists()
    found = svc.search(module="gameplay.Jigsaw", query="奖励重复")
    assert [i["id"] for i in found["items"]] == [written["id"]]
    assert found["module"] == "gameplay.Jigsaw"


def test_alias_and_entity_are_normalised(svc):
    written = record(svc, module="puzzle", entity="奖励")
    assert written["module"] == "gameplay.Jigsaw"
    assert written["entity"] == "Reward"


def test_search_by_path_maps_to_module(svc):
    written = record(svc)
    found = svc.search(path="src/Jigsaw/Board.cs")
    assert found["module"] == "gameplay.Jigsaw"
    assert found["resolved_from"] == "path"
    assert found["items"][0]["id"] == written["id"]


def test_search_unmapped_path_says_so(svc):
    found = svc.search(path="tools/build.py")
    assert found["ok"] is True
    assert found["module"] is None
    assert "未登记" in found["hint"]


def test_search_unknown_module_reports_similar(svc):
    found = svc.search(module="gameplay.Jigsow")
    assert found["module_exists"] is False
    assert "gameplay.Jigsaw" in found["similar_modules"]


def test_search_requires_module_path_or_query(svc):
    assert svc.search()["ok"] is False


def test_global_search_with_query(svc):
    written = record(svc)
    found = svc.search(query="防连点")
    assert found["items"][0]["id"] == written["id"]
    assert found["items"][0]["module"] == "gameplay.Jigsaw"


def test_unknown_category_is_rejected(svc):
    result = record(svc, module="ui.Button")
    assert result["ok"] is False
    assert "activity / gameplay / economy / infra" in result["error"]


def test_new_module_is_written_and_flagged(svc):
    result = record(svc, module="activity.WorldCup", entity="Schedule")
    assert result["ok"] is True
    assert result["new_module"] is True


def test_candidate_module_is_flagged(svc):
    result = record(svc, module="activity.ladybug", entity="Schedule")
    assert result["ok"] is True
    assert result["module"] == "activity.Ladybug"
    assert result["candidate_module"] is True


def test_content_length_is_checked(svc):
    assert record(svc, content="太短")["ok"] is False
    assert record(svc, content="长" * 1300)["ok"] is False


def test_good_memory_has_no_hints(svc):
    assert "hints" not in record(svc, aliases=["领奖"])
    assert "hints" not in record(svc, entity="Popup", aliases=["弹框"],
                                 content="商店弹窗的根因：动画回调里重复调用了 Open，导致连弹两次。")


def test_missing_aliases_get_a_hint(svc):
    assert any("aliases" in h for h in record(svc)["hints"])


def test_record_returns_similar_memories_for_agent_to_reconcile(svc):
    old = record(svc, aliases=["领奖"], content="奖励重复发放的根因：领取按钮没有防连点，连续点击会发两次。")
    new = record(svc, aliases=["领奖"], content="奖励重复发放：除了按钮防连点，服务端也要按订单号去重，避免弱网重试重复发。")
    assert [s["id"] for s in new["similar"]] == [old["id"]]
    assert any("supersedes" in h for h in new["hints"])
    replaced = record(svc, aliases=["领奖"], supersedes=[old["id"], new["id"]],
                      content="奖励重复发放的根因与对策：按钮防连点 + 服务端按订单号去重，二者缺一都会重复发。")
    assert "similar" not in replaced


def test_confirm_refreshes_verified_date(svc, project):
    written = record(svc, aliases=["领奖"])
    result = svc.confirm([written["id"], "01JA7K3M2X9F4Q8W6ZB1C2D3E4"])
    assert result["confirmed"] == [written["id"]] and result["missing"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    text = next((project / ".memory" / "entries").rglob(f"{written['id']}.md")).read_text(encoding="utf-8")
    assert f"verified: '{result['verified']}'" in text


def test_graph_marks_stale_current_memories(svc, project):
    gone = record(svc, anchors=["src/Jigsaw/Gone.cs"])
    fine = record(svc, entity="Server", content=LONG + "服务端")
    overview = svc.graph("gameplay.Jigsaw")
    rows = {row["id"]: row for topic in overview["topics"] for row in topic["latest"]}
    assert rows[gone["id"]]["stale"] is True and rows[gone["id"]]["check"] == ["src/Jigsaw/Gone.cs 已不存在"]
    assert "stale" not in rows[fine["id"]]
    assert "verify_hint" in overview
    timeline = svc.graph("gameplay.Jigsaw", entity="Reward")["timeline"]
    assert timeline[0]["stale"] is True


def test_anchors_are_stored_relative_with_on_disk_case(svc, project):
    board = project / "src" / "Jigsaw" / "Board.cs"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text("class Board { void Claim() {} }", encoding="utf-8")
    written = record(svc, anchors=[f"{board}#Claim", "./src/jigsaw/board.cs", "src/Jigsaw/Gone.cs"])
    entry = svc.storage.get(written["id"])
    assert entry.anchors == ["src/Jigsaw/Board.cs#Claim", "src/Jigsaw/Board.cs", "src/Jigsaw/Gone.cs"]
    assert any("Gone.cs 在项目里不存在" in w for w in written["warnings"])


def test_search_rejects_bad_as_of(svc):
    assert svc.search(module="gameplay.Jigsaw", as_of="昨天")["ok"] is False


def test_changelog_and_new_entity_get_hints_but_are_written(svc):
    record(svc)
    result = record(svc, entity="RewardPopup", content="新增了奖励弹窗的关闭按钮和动画。")
    assert result["ok"] is True
    hints = "\n".join(result["hints"])
    assert "变更记录" in hints and "RewardPopup" in hints and "相近的已有：Reward" in hints
    assert "draft_id" in hints


def test_invalid_kind_is_rejected(svc):
    result = record(svc, kind="note")
    assert result["ok"] is False
    assert "kind" in result["error"]


def test_secret_is_rejected_with_location(svc):
    result = record(svc, content="接口调用需要 api_key = sk_live_abcdefghijklmnop 才能访问后台")
    assert result["ok"] is False
    assert "敏感" in result["error"]


def test_daily_cap_rejects_and_lists_existing(svc):
    first = record(svc)
    second = record(svc, content=LONG + "补充一")
    third = record(svc, content=LONG + "补充二")
    assert third["ok"] is False
    assert set(third["existing_ids"]) == {first["id"], second["id"]}


def test_draft_overwrite_keeps_id(svc):
    first = record(svc)
    again = record(svc, content=LONG + "更新", draft_id=first["id"])
    assert again["ok"] is True
    assert again["id"] == first["id"]
    assert again["overwritten"] is True
    found = svc.search(module="gameplay.Jigsaw")
    assert len(found["items"]) == 1
    assert found["items"][0]["content"].endswith("更新")


def test_draft_overwrite_keeps_lists_that_were_not_passed(svc):
    old = record(svc, entity="Config")
    first = record(svc, supersedes=[old["id"]], anchors=["src/Jigsaw/Board.cs#Claim"], aliases=["连点"])
    record(svc, content=LONG + "更新", draft_id=first["id"])
    entry = svc.index.find(first["id"])
    assert entry.supersedes == [old["id"]]
    assert entry.anchors == ["src/Jigsaw/Board.cs#Claim"]
    assert entry.aliases == ["连点"]
    assert [i["id"] for i in svc.search(module="gameplay.Jigsaw")["items"]] == [first["id"]]


def test_draft_overwrite_clears_lists_passed_empty(svc):
    old = record(svc, entity="Config")
    first = record(svc, supersedes=[old["id"]], aliases=["连点"])
    record(svc, content=LONG + "更新", draft_id=first["id"], supersedes=[], aliases=[])
    entry = svc.index.find(first["id"])
    assert entry.supersedes == [] and entry.aliases == []


def test_draft_overwrite_is_exempt_from_daily_cap(svc):
    first = record(svc)
    record(svc, content=LONG + "补充一")
    again = record(svc, content=LONG + "更新", draft_id=first["id"])
    assert again["ok"] is True


def test_supersedes_hides_old(svc):
    old = record(svc)
    new = record(svc, kind="correction", content="更正：" + LONG, supersedes=[old["id"]])
    ids = [i["id"] for i in svc.search(module="gameplay.Jigsaw")["items"]]
    assert ids == [new["id"]]


def test_unknown_supersedes_id_warns(svc):
    result = record(svc, supersedes=["01JA7K3M2X9F4Q8W6ZB1C2D3E9"])
    assert result["ok"] is True
    assert any("01JA7K3M2X9F4Q8W6ZB1C2D3E9" in w for w in result["warnings"])


def test_list_modules(svc):
    record(svc)
    record(svc, module="activity.WorldCup", entity="Schedule")
    listing = svc.list_modules()
    by_id = {m["module"]: m for m in listing["modules"]}
    assert by_id["gameplay.Jigsaw"]["count"] == 1
    assert by_id["gameplay.Jigsaw"]["aliases"] == ["Puzzle"]
    assert by_id["activity.WorldCup"]["registered"] is False
    assert "economy.Shop" in listing["registered_empty"]
    assert "economy.Shop" not in by_id


def test_modules_yaml_changes_are_picked_up(svc, project):
    path = project / ".memory" / "modules.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("Puzzle", "PuzzleGame"), encoding="utf-8")
    import os
    import time

    os.utime(path, (time.time() + 5, time.time() + 5))
    assert record(svc, module="PuzzleGame")["module"] == "gameplay.Jigsaw"


def test_broken_modules_yaml_gives_readable_error(svc, project):
    path = project / ".memory" / "modules.yaml"
    path.write_text("modules:\n  gameplay.Jigsaw:\n    label: a  b: c\n", encoding="utf-8")
    for result in (svc.list_modules(), svc.search(query="奖励", entity="Reward"), record(svc)):
        assert result["ok"] is False
        assert "modules.yaml 第 3 行格式错误" in result["error"]
