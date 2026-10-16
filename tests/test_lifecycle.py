from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.index.graph import current_entries
from pmem.metrics.events import read_events
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
TEXT = "奖励重复发放的根因：配置缺字段时回退到默认奖励，导致重复发放。"


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    monkeypatch.delenv("PMEM_NO_EVENTS", raising=False)
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    (root / "src" / "Jigsaw" / "Reward.cs").write_text("class Reward {}\n", encoding="utf-8")
    return root


@pytest.fixture
def svc(project):
    service = MemoryService(project)
    yield service
    service.close()


def _ids(svc, **kwargs) -> list[str]:
    return [i["id"] for i in svc.search(**kwargs)["items"]]


def test_archive_hides_memory_and_restore_brings_it_back(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    result = svc.change_status([rid], "archive")
    assert result["ok"] and result["changed"] == [rid]
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励") == []
    assert svc.storage.get(rid).status == "archived"
    assert svc.change_status([rid], "archive")["skipped"] == [{"id": rid, "status": "archived"}]
    assert svc.change_status([rid], "restore")["changed"] == [rid]
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励") == [rid]


def test_superseding_own_draft_creates_a_new_memory(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    again = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT + "更新。", draft_id=rid, supersedes=[rid])
    assert again["ok"] and not again["overwritten"] and again["id"] != rid
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励") == [again["id"]]


def test_archived_draft_cannot_be_overwritten(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    svc.change_status([rid], "archive")
    again = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT + "补充。", draft_id=rid)
    assert again["ok"] is False and "已归档" in again["error"]
    assert svc.storage.get(rid).status == "archived"


def test_bad_archived_header_falls_back_to_active(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    svc.change_status([rid], "archive")
    path = svc.storage.find_path(rid)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("from: active", "from: bogus"), encoding="utf-8")
    assert svc.change_status([rid], "restore")["changed"] == [rid]
    assert svc.storage.get(rid).status == "active"
    path.write_text(path.read_text(encoding="utf-8").replace("status: active", "status: archived\narchived: oops"),
                    encoding="utf-8")
    assert svc.storage.get(rid).archived_on is None


def test_restore_returns_rejected_seed_to_seed(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="seed")["id"]
    svc.change_status([rid], "reject")
    entry = svc.storage.get(rid)
    assert (entry.status, entry.archived_from) == ("archived", "seed") and entry.archived_on
    assert entry.archived_by == svc.user
    svc.change_status([rid], "restore")
    entry = svc.storage.get(rid)
    assert (entry.status, entry.archived_on, entry.archived_from) == ("seed", None, None)
    assert entry.archived_by is None


def test_as_of_still_sees_memories_archived_later(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    svc.change_status([rid], "archive")
    path = svc.storage.find_path(rid)
    entry = svc.storage.read(path)
    day = entry.note_date
    entry.archived_on = "2999-01-01"
    path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
    svc.index.refresh(force=True)
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励") == []
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励", as_of=day) == [rid]
    entry.archived_on = None
    path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
    svc.index.refresh(force=True)
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励", as_of=day) == []


def test_archiving_a_merged_memory_keeps_replaced_ones_hidden(svc):
    old = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    merged = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT + "合并后。", supersedes=[old])["id"]
    svc.change_status([merged], "archive")
    assert _ids(svc, module="gameplay.Jigsaw", query="奖励") == []
    assert current_entries(svc.index.entries()) == []
    timeline = svc.graph("gameplay.Jigsaw", "Reward")["timeline"]
    assert [(r["id"], r.get("superseded_by")) for r in timeline] == [(old, merged)]


def test_report_assets_skip_archived_memories(project, svc):
    from pmem.metrics.report import build_report

    keep = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    gone = svc.record("economy.Shop", "Price", "risk", "价格表缓存不会自动刷新，因此改价后必须清缓存，否则显示旧价。")["id"]
    svc.change_status([gone], "archive")
    assert keep and build_report(project, heat=False)["assets"]["memories"] == 1


def test_seed_label_in_brief_output(project, svc, capsys):
    svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="seed")
    assert main(["search", "--root", str(project), "--module", "gameplay.Jigsaw", "--brief", "奖励"]) == 0
    assert "（种子，待确认）" in capsys.readouterr().out


def test_archive_cli_reports_missing_ids(project, svc, capsys):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    assert main(["archive", rid, "--root", str(project)]) == 0
    assert main(["archive", "01ARZ3NDEKTSV4RRFFQ69G5FAV", "--root", str(project)]) == 1
    assert "missing" in capsys.readouterr().out
    assert main(["archive", rid, "--restore", "--root", str(project)]) == 0


def test_seed_memories_are_searchable_and_marked_until_accepted(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="seed")["id"]
    items = svc.search(module="gameplay.Jigsaw", query="奖励")["items"]
    assert [(i["id"], i.get("status")) for i in items] == [(rid, "seed")]
    assert [r["id"] for r in svc.seeds()["seeds"]] == [rid]
    assert svc.change_status([rid], "accept")["changed"] == [rid]
    assert svc.storage.get(rid).status == "active"
    assert svc.seeds()["seeds"] == []


def test_overwriting_a_seed_draft_keeps_seed_status(svc):
    rid = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="seed")["id"]
    again = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT + "补充。", draft_id=rid)
    assert again["overwritten"] and svc.storage.get(rid).status == "seed"


def test_invalid_status_and_rejections_are_logged(svc):
    bad = svc.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="archived")
    assert bad["ok"] is False and "status" in bad["error"]
    assert svc.record("gameplay.Jigsaw", "Reward", "conclusion", "太短")["ok"] is False
    rejected = [e for e in read_events(svc.config.cache_dir) if e["type"] == "record_rejected"]
    assert [e["module"] for e in rejected] == ["gameplay.Jigsaw", "gameplay.Jigsaw"]
    assert "正文长度" in rejected[1]["error"]


def test_seed_cli_flow(project, capsys):
    assert main(["record", "--root", str(project), "--seed", "--module", "gameplay.Jigsaw", "--entity", "Reward",
                 "--kind", "conclusion", "--content", TEXT]) == 0
    assert main(["record", "--root", str(project), "--seed", "--module", "economy.Shop", "--entity", "Price",
                 "--kind", "risk", "--content", "价格表缓存不会自动刷新，因此改价后必须清缓存，否则显示旧价。"]) == 0
    capsys.readouterr()
    assert main(["seed", "--root", str(project)]) == 0
    out = capsys.readouterr().out
    assert "待确认的种子记忆 2 条" in out and "gameplay.Jigsaw（1 条）" in out
    assert main(["seed", "--plan", "--root", str(project)]) == 0
    assert "gameplay.Jigsaw" in capsys.readouterr().out
    assert main(["seed", "--accept", "--root", str(project)]) == 2
    assert main(["seed", "--accept", "--module", "Jigsaw", "--root", str(project)]) == 0
    assert "已转为正式记忆 1 条" in capsys.readouterr().out
    service = MemoryService(project)
    try:
        left = service.seeds()["seeds"]
    finally:
        service.close()
    assert [r["module"] for r in left] == ["economy.Shop"]
    assert main(["seed", "--reject", left[0]["id"], "--root", str(project)]) == 0
    assert "已退回（已归档） 1 条" in capsys.readouterr().out
