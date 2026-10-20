"""v0.3.2：合并回滚、记忆图与自检、健康报告的跳过复查和清理候选。"""
import time
from pathlib import Path

import pytest

from pmem.cli.map_cmd import run_map
from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.generate.memmap import render_map_html, render_mermaid
from pmem.generate.wiki import render_wiki
from pmem.index.memmap import build_map
from pmem.metrics.cleanup import cleanup_candidates
from pmem.metrics.health import _skipped
from pmem.metrics.memmap import _broken
from pmem.scan.files import code_mentions
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwrite: { content_min: 10 }\n"
MODULES = """
categories: { gameplay: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
"""
TEXT = "结论：奖励在服务端发放，客户端只展示结果，因为多端登录会重复领取。"


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


@pytest.fixture
def svc(project):
    service = MemoryService(project)
    yield service
    service.close()


def _write(svc, entity="Reward", kind="conclusion", content=TEXT, **kw) -> str:
    result = svc.record("gameplay.Jigsaw", entity, kind, content, **kw)
    assert result["ok"], result
    return result["id"]


_clock = [int(time.time() * 1000)]


def _mk(kind: str, entity: str = "Reward", day: str = "2026-10-01", **kw) -> Entry:
    _clock[0] += 1
    return Entry(id=new_ulid(_clock[0]), module="gameplay.Jigsaw", entity=entity, kind=kind,
                 content=kw.pop("content", f"{kind} 的正文"), note_date=day, author="alice", **kw)


# ---- 合并回滚 ----

def test_revert_restores_merged_memories_and_restore_redoes(svc):
    a, b = _write(svc), _write(svc, content=TEXT + "补充：活动奖励同样处理。")
    merged = _write(svc, content=TEXT + "合并后的完整现状。", supersedes=[a, b])
    assert {a, b} <= svc.index.superseded()
    result = svc.revert(merged)
    assert result["ok"] and sorted(result["restored"]) == sorted([a, b])
    entry = svc.index.find(merged)
    assert entry.status == "archived" and entry.reverted_on and entry.reverted_by == "alice"
    assert not {a, b} & svc.index.superseded()
    assert not svc.revert(merged)["ok"]
    svc.change_status([merged], "restore")
    again = svc.index.find(merged)
    assert again.status == "active" and again.reverted_on is None and {a, b} <= svc.index.superseded()


def test_revert_refuses_plain_or_already_replaced_entries(svc):
    plain = _write(svc)
    assert "没有替代任何记忆" in svc.revert(plain)["error"]
    merged = _write(svc, content=TEXT + "第二版。", supersedes=[plain])
    _write(svc, content=TEXT + "第三版。", supersedes=[merged])
    assert "已被" in svc.revert(merged)["error"]
    assert "找不到" in svc.revert("01M00000000000000000000000")["error"]


def test_revert_keeps_archived_originals_hidden(svc):
    old = _write(svc)
    merged = _write(svc, content=TEXT + "合并版。", supersedes=[old])
    svc.change_status([old], "archive")
    result = svc.revert(merged)
    assert result["restored"] == [] and result["not_restored"][0]["id"] == old


def test_replaces_respects_revert_date_and_round_trips():
    entry = _mk("conclusion", supersedes=["X"], reverted_on="2026-10-20", reverted_by="bob", status="archived")
    assert entry.replaces() == [] and entry.replaces("2026-10-21") == []
    assert entry.replaces("2026-10-19") == ["X"]
    again = Entry.from_markdown(entry.to_markdown())
    assert again.reverted_on == "2026-10-20" and again.reverted_by == "bob" and again.extra == {}


# ---- 记忆图 ----

def _topic(model: dict, entity: str) -> dict:
    return next(t for m in model["modules"] for t in m["topics"] if t["entity"] == entity)


def test_map_infers_landing_after_exclusion_and_flags_unresolved():
    tried = _mk("exclusion", day="2026-10-01")
    landed = _mk("decision", day="2026-10-02")
    stuck = _mk("exclusion", entity="Cache", day="2026-10-03")
    model = build_map([tried, landed, stuck])
    reward = _topic(model, "Reward")
    assert reward["edges"] == [{"from": tried.id, "to": landed.id, "type": "inferred"}]
    assert reward["unresolved"] is None and _topic(model, "Cache")["unresolved"] == stuck.id
    assert model["current"] == 3 and model["total"] == 3


def test_map_marks_supersedes_and_reverted_edges():
    old = _mk("conclusion", day="2026-10-01")
    fix = _mk("correction", day="2026-10-02", supersedes=[old.id])
    other = _mk("conclusion", entity="Shop", day="2026-10-01")
    undone = _mk("decision", entity="Shop", day="2026-10-03", supersedes=[other.id], status="archived",
                 reverted_on="2026-10-04")
    model = build_map([old, fix, other, undone])
    assert _topic(model, "Reward")["edges"] == [{"from": old.id, "to": fix.id, "type": "supersedes"}]
    shop = _topic(model, "Shop")
    assert shop["edges"][0]["type"] == "reverted"
    nodes = {n["id"]: n for n in shop["nodes"]}
    assert nodes[other.id]["current"] and nodes[undone.id]["reverted"] == "2026-10-04"
    assert not {n["id"]: n for n in _topic(model, "Reward")["nodes"]}[old.id]["current"]


def test_broken_lists_corrections_without_supersedes():
    old = _mk("conclusion")
    linked = _mk("correction", supersedes=[old.id], content="更正：奖励不在客户端去重")
    orphan = _mk("correction", entity="Shop", content="更正：价格单位是分")
    rows = _broken([old, linked, orphan])
    assert [r["ids"] for r in rows] == [[orphan.id]]


def test_mermaid_escapes_labels_and_skips_single_node():
    a = _mk("exclusion", entity='A"<b>#1', content='不要用 "<script>" #标签')
    b = _mk("decision", entity='A"<b>#1', day="2026-10-02")
    module = build_map([a, b], full=False)["modules"][0]
    text = render_mermaid(module)
    assert text.startswith("```mermaid") and "-.->|推断|" in text
    assert "#34;#60;b#62;#35;1" in text and "<script>" not in text
    assert render_mermaid(build_map([_mk("risk")])["modules"][0]) is None


def test_html_embeds_data_without_closing_script():
    entry = _mk("risk", content="正文里有 </script><b>")
    page = render_map_html({**build_map([entry]), "title": "<demo>"})
    assert "<\\/script><b>" in page and "&lt;demo&gt;" in page
    assert page.count("</script>") == render_map_html({"modules": [], "title": ""}).count("</script>")


def test_map_command_writes_html_and_summary(svc, project, capsys):
    a = _write(svc, kind="exclusion", content="排除：不要在客户端去重奖励，因为多端登录会绕过。")
    _write(svc, content=TEXT, supersedes=[a])
    assert run_map(project, None, 30, False) == 0
    out = capsys.readouterr().out
    page = project / ".memory" / "wiki" / "map.html"
    assert "记忆图：1 个模块" in out and page.is_file() and (page.parent / ".gitignore").is_file()
    assert a in page.read_text(encoding="utf-8")


def test_wiki_module_page_has_evolution_diagram(svc, tmp_path):
    a = _write(svc, kind="exclusion", content="排除：不要在客户端去重奖励，因为多端登录会绕过。")
    _write(svc, content=TEXT, supersedes=[a])
    pages = render_wiki(svc, tmp_path / "wiki")
    assert any("## 演化图" in page and "```mermaid" in page for page in pages.values())


# ---- 健康报告：跳过复查与清理候选 ----

def test_skipped_counts_modules_without_feature_records():
    now = time.time()
    events = [{"type": "stop", "conv": "c1", "ts": now, "required": ["m.A", "m.B"]},
              {"type": "stop", "conv": "c2", "ts": now, "required": ["m.B"]}]
    feature = Entry(id=new_ulid(int(now * 1000)), module="m.A", entity="E", kind="feature", content="x",
                    note_date="2026-10-20", author="alice", source_conversation="c1")
    assert _skipped(events, [feature], "alice", now - 3600) == [("m.B", 2)]


def test_code_mentions_only_count_source_files_and_paths():
    text = "Next.js 项目里 config.yaml、src/app/config.yaml、board.py 和 BoardView.render 都提到了"
    assert code_mentions(text) == [("path", "src/app/config.yaml"), ("path", "board.py"), ("class", "BoardView")]


def test_cleanup_archives_only_when_every_criterion_holds(svc, project):
    (project / "src" / "Jigsaw").mkdir(parents=True)
    (project / "src" / "Jigsaw" / "Board.cs").write_text("class Board {}", encoding="utf-8")
    (project / "src" / "Jigsaw" / "views.py").write_text("class BoardView:\n    pass\n", encoding="utf-8")
    gone = _mk("conclusion", entity="Old", anchors=["src/Jigsaw/Gone.cs#Run"])
    risky = _mk("risk", entity="Old2", anchors=["src/Jigsaw/Gone.cs"])
    alive = _mk("conclusion", entity="Live", anchors=["src/Jigsaw/Gone.cs", "src/Jigsaw/Board.cs"])
    faded = _mk("decision", entity="Faded", content="决定：src/Jigsaw/Old.cs 和 OldThing.Run 负责发奖")
    python = _mk("decision", entity="Py", content="决定：BoardView.render 和 src/Jigsaw/Missing.cs 负责展示")
    cited = _mk("conclusion", entity="Cited", anchors=["src/Jigsaw/Gone.cs"])
    citing = _mk("conclusion", entity="Citing", anchors=["src/Jigsaw/Board.cs"], content=f"见 {cited.id} 的结论")
    entries = [gone, risky, alive, faded, python, cited, citing]
    result = cleanup_candidates(project, svc.registry, entries, None)
    assert [r["id"] for r in result["archive"]] == [gone.id]
    review = {r["id"]: r for r in result["review"]}
    assert set(review) == {risky.id, faded.id, cited.id}
    assert any("不建议直接归档" in b for b in review[risky.id]["basis"])
    assert "✓ 正文提到的文件或类在代码里找到 0/2" in review[faded.id]["basis"]
    assert "✗ 没有被其他记忆引用" in review[cited.id]["basis"]
    used = cleanup_candidates(project, svc.registry, entries, {gone.id})
    assert not used["archive"] and "✗ 统计期内本机没被用过" in {r["id"]: r for r in used["review"]}[gone.id]["basis"]
