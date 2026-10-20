"""v0.3.1 功能记录与分层检索：feature / plan 类型、applies、教训与功能记录分组、摘要与拦截、免记录文件、度量。"""
import json
import time
from pathlib import Path

import pytest

from pmem.cli.brief import render_brief
from pmem.cli.main import build_parser
from pmem.core.config import Config
from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints
from pmem.generate.templates import COMPACT_SKILL, RULE_BODY
from pmem.hooks.gate import handle
from pmem.metrics.report import _feature_coverage, _pitfall_share, _render_quality
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwrite: { content_min: 10 }\n"
GATE_CONFIG = "project: { name: demo }\nvcs: none\ngate: { mode: block }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
FEATURE = "用户要求：拼图完成后必须弹出分享面板，iOS 审核期间也要保持，不能当成冗余去掉。入口在 Board.Finish。"
LESSON = "排除：不要在客户端去重奖励，因为多端登录会绕过，必须走服务端。"


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
def svc(project):
    service = MemoryService(project)
    yield service
    service.close()


def write(svc, **kw):
    args = {"module": "gameplay.Jigsaw", "entity": "Share", "kind": "feature", "content": FEATURE}
    args.update(kw)
    result = svc.record(**args)
    assert result["ok"], result
    return result


# ---- 数据模型与写入 ----

def test_feature_kind_and_applies_round_trip():
    entry = Entry(id=new_ulid(), module="gameplay.Jigsaw", entity="Share", kind="feature", content=FEATURE,
                  note_date="2026-10-19", author="a", applies="仅 iOS 版本 ≥ 3.2")
    again = Entry.from_markdown(entry.to_markdown())
    assert again.kind == "feature" and again.applies == "仅 iOS 版本 ≥ 3.2" and again.extra == {}
    assert "applies" not in Entry(id=new_ulid(), module="m.A", entity="E", kind="plan", content="规划内容",
                                  note_date="2026-10-19", author="a").to_markdown()


def test_record_feature_with_applies_and_inherits_on_draft(svc):
    first = write(svc, applies="只在审核模式下")
    assert svc.index.find(first["id"]).applies == "只在审核模式下"
    again = write(svc, draft_id=first["draft_id"], content=FEATURE + "补充：安卓同样保持。")
    assert svc.index.find(again["id"]).applies == "只在审核模式下"


def test_record_rejects_overlong_applies(svc):
    result = svc.record("gameplay.Jigsaw", "Share", "feature", FEATURE, applies="长" * 121)
    assert not result["ok"] and result["code"] == "content_length"


def test_feature_hints_ask_for_requirement_not_reason():
    assert any("需求来源" in h for h in content_hints("新增分享面板，在 Board 里弹出。", 600, "feature"))
    assert content_hints(FEATURE, 600, "feature") == []
    assert not any("需求来源" in h for h in content_hints(LESSON, 600, "exclusion"))


# ---- 分层检索 ----

def test_search_splits_lessons_and_feature_titles(svc):
    feature = write(svc)
    lesson = write(svc, entity="Reward", kind="exclusion", content=LESSON)
    result = svc.search(module="gameplay.Jigsaw", query="分享 奖励")
    assert [i["id"] for i in result["items"]] == [lesson["id"]]
    row = result["features"][0]
    assert row["id"] == feature["id"] and row["kind"] == "feature" and "content" not in row
    assert row["summary"] and "改回去" in result["features_hint"]


def test_features_do_not_crowd_out_lessons(svc):
    for n in range(6):
        write(svc, entity=f"F{n}", content=FEATURE + f"（第 {n} 个）", source_conversation=f"c{n}")
    lesson = write(svc, entity="Reward", kind="risk", content=LESSON)
    result = svc.search(module="gameplay.Jigsaw", query="分享面板", limit=3)
    assert [i["id"] for i in result["items"]] == [lesson["id"]]
    assert len(result["features"]) == 3


def test_feature_limit_zero_hides_group(project):
    (project / ".memory" / "config.yaml").write_text(CONFIG + "search: { feature_limit: 0 }\n", encoding="utf-8")
    service = MemoryService(project)
    try:
        write(service)
        result = service.search(module="gameplay.Jigsaw")
        assert result["items"] == [] and "features" not in result
    finally:
        service.close()


def test_ids_return_full_text_and_report_missing(svc):
    feature = write(svc, applies="仅 iOS")
    result = svc.search(ids=[feature["id"], "01JA7K3M2X9F4Q8W6ZB1C2D3E4"], source_conversation="c1")
    item = result["items"][0]
    assert item["content"].startswith("用户要求") and item["module"] == "gameplay.Jigsaw" and item["applies"] == "仅 iOS"
    assert result["missing"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    again = svc.search(ids=[feature["id"]], source_conversation="c1")
    assert "content" in again["items"][0] and not again["items"][0].get("seen")


def test_applies_hint_when_any_row_has_conditions(svc):
    write(svc, entity="Reward", kind="risk", content=LESSON, applies="多端登录开启时")
    result = svc.search(module="gameplay.Jigsaw")
    assert result["items"][0]["applies"] == "多端登录开启时" and "前提" in result["applies_hint"]


def test_plan_is_grouped_with_features(svc):
    plan = write(svc, entity="Ranking", kind="plan", content="规划：用户要求以后加好友排行榜，暂未实现。")
    result = svc.search(module="gameplay.Jigsaw")
    assert result["items"] == [] and result["features"][0]["id"] == plan["id"]


# ---- 闸门：摘要、拦截、结束提醒 ----

def _entry(root: Path, module: str, kind: str, content: str, extra: str = "", entity: str = "Reward") -> str:
    entry_id = new_ulid()
    folder = root / ".memory" / "entries" / module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{entry_id}.md").write_text(
        f"---\nid: {entry_id}\nmodule: {module}\nentity: {entity}\nkind: {kind}\nstatus: active\nauthor: a\n"
        f"note_date: '2026-10-01'\n{extra}---\n{content}\n", encoding="utf-8")
    return entry_id


@pytest.fixture
def gate_root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "gate"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(GATE_CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


def _read(root: Path, rel: str, conv: str = "c1") -> str:
    result = handle("post-tool", {"conversation_id": conv, "tool_name": "Read",
                                  "tool_input": {"path": str(root / rel)}}, root)
    return result.get("additional_context", "")


def test_digest_lists_lessons_and_only_features_of_this_file(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "risk", "风险：奖励接口不幂等。")
    _entry(gate_root, "gameplay.Jigsaw", "feature", "用户要求：完成后弹分享面板。", "anchors: [src/Jigsaw/Board.cs]\n",
           entity="Share")
    _entry(gate_root, "gameplay.Jigsaw", "feature", "用户要求：设置页有静音开关。", "anchors: [src/Jigsaw/Settings.cs]\n",
           entity="Mute")
    text = _read(gate_root, "src/Jigsaw/Board.cs")
    assert "风险｜Reward" in text and "功能｜Share" in text and "静音" not in text


def test_guard_lists_feature_records_of_target_file(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "feature", "用户要求：完成后弹分享面板。", "anchors: [src/Jigsaw/Board.cs#Finish]\n",
           entity="Share")
    denied = handle("pre-tool", {"conversation_id": "c1", "tool_name": "Write",
                                 "tool_input": {"file_path": str(gate_root / "src/Jigsaw/Board.cs")}}, gate_root)
    message = denied["user_message"]
    assert denied["permission"] == "deny" and "这个文件上的功能记录" in message and "完成后弹分享面板" in message


def _stop(root: Path, conv: str = "c1") -> dict:
    return handle("stop", {"conversation_id": conv, "status": "completed"}, root)


def _edit(root: Path, rel: str, conv: str = "c1") -> None:
    handle("edited", {"conversation_id": conv, "file_path": str(root / rel)}, root)


def test_exempt_files_do_not_trigger_record_reminder(gate_root):
    _edit(gate_root, "src/Shop/tests/test_shop.py")
    _edit(gate_root, "src/Shop/shop.json")
    assert "followup_message" not in _stop(gate_root)
    _edit(gate_root, "src/Shop/Shop.cs", conv="c2")
    _edit(gate_root, "src/Shop/shop.json", conv="c2")
    assert "kind=feature" in _stop(gate_root, "c2")["followup_message"]


def test_stop_event_logs_required_modules(gate_root):
    _edit(gate_root, "src/Shop/Shop.cs")
    _edit(gate_root, "src/Jigsaw/tests/test_board.py")
    _stop(gate_root)
    lines = (Config.load(gate_root).cache_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    stop = [json.loads(line) for line in lines if '"stop"' in line][-1]
    assert stop["required"] == ["economy.Shop"] and set(stop["edited"]) == {"economy.Shop", "gameplay.Jigsaw"}


# ---- 度量 ----

def _mk(kind: str, module: str = "m.A", conv: str | None = None, ts: float | None = None) -> Entry:
    return Entry(id=new_ulid(int((ts or time.time()) * 1000)), module=module, entity="E", kind=kind, content="x",
                 note_date="2026-10-19", author="alice", source_conversation=conv)


def test_pitfall_share_ignores_feature_records():
    now = time.time()
    rows = [_mk("feature"), _mk("feature"), _mk("plan"), _mk("risk"), _mk("decision")]
    assert _pitfall_share(rows, now - 86400) == {"new": 2, "new_pitfalls": 1, "old": 0, "old_pitfalls": 0}


def test_feature_coverage_counts_by_conversation_or_time_window():
    now = time.time()
    events = [
        {"type": "stop", "conv": "c1", "ts": now, "required": ["m.A", "m.B"]},
        {"type": "stop", "conv": "c2", "ts": now, "required": ["m.C"]},
        {"type": "stop", "conv": "c3", "ts": now, "edited": ["m.D"]},
    ]
    convs = {"c1": {"start": now - 600, "end": now}, "c2": {"start": now - 600, "end": now}}
    mine = [_mk("feature", "m.A", conv="c1"), _mk("feature", "m.C", ts=now - 300), _mk("risk", "m.B", conv="c1")]
    coverage = _feature_coverage(events, convs, mine)
    assert coverage == {"required": 3, "covered": 2}
    line = _render_quality(None, None, coverage)[0]
    assert "67%" in line and "偏低" in line


# ---- 命令行与模板 ----

def test_brief_renders_feature_group_and_applies():
    result = {"ok": True, "module": "gameplay.Jigsaw", "items": [
        {"id": "A", "entity": "Reward", "kind": "risk", "date": "2026-10-19", "content": "风险：不幂等。",
         "applies": "多端登录"}],
        "features": [{"id": "F", "entity": "Share", "kind": "feature", "date": "2026-10-19", "summary": "完成后弹分享",
                      "stale": False}],
        "applies_hint": "带 applies 的记忆只在该前提下成立"}
    text = render_brief("search", result)
    assert "适用：多端登录" in text and "功能记录与规划 1 条" in text and "功能｜Share｜2026-10-19｜F：完成后弹分享" in text
    assert "提示：带 applies" in text


def test_cli_accepts_feature_kind_applies_and_ids():
    parser = build_parser()
    args = parser.parse_args(["record", "--module", "m.A", "--entity", "E", "--kind", "feature", "--content", "x",
                              "--applies", "仅 iOS"])
    assert args.kind == "feature" and args.applies == "仅 iOS"
    assert parser.parse_args(["search", "--id", "A", "B"]).ids == ["A", "B"]


def test_rule_and_compact_skill_describe_two_layers():
    assert "功能记录（改了模块就写）" in RULE_BODY and "search_memory(ids=[...])" in RULE_BODY
    assert "适用条件不同的记忆不合并" in COMPACT_SKILL
