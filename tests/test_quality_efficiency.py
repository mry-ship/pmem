"""v0.3 记忆质量与上下文效率：标题、验证方法、全项目级坑、对话内去重、写作提示与度量。"""
import json
import time
from pathlib import Path

import pytest

from pmem.cli.brief import render_brief
from pmem.core import seen
from pmem.core.config import Config
from pmem.core.entry import Entry, auto_summary
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints, verify_hint
from pmem.hooks.gate import handle
from pmem.metrics.health import _cross_module_supersedes, _repeat_corrections, reject_reason
from pmem.metrics.report import _pitfall_share, _render_quality, _repeats
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwrite: { content_min: 10 }\n"
GATE_CONFIG = "project: { name: demo }\nvcs: none\ngate: { mode: block }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
CONTENT = "拼图奖励重复发放的根因是领取按钮没有防连点。"


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
    args = {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": CONTENT}
    args.update(kw)
    result = svc.record(**args)
    assert result["ok"], result
    return result


# ---- 数据模型 ----

def test_new_fields_round_trip_and_old_files_still_parse():
    entry = Entry(id=new_ulid(), module="gameplay.Jigsaw", entity="Reward", kind="risk", content="正文内容足够长",
                  note_date="2026-10-19", author="a", summary="一句话结论", scope="project", verify="跑 test_reward\n看日志")
    again = Entry.from_markdown(entry.to_markdown())
    assert (again.summary, again.scope, again.verify) == ("一句话结论", "project", "跑 test_reward\n看日志")
    assert again.project_wide and again.title == "一句话结论" and again.extra == {}
    plain = Entry.from_markdown(entry.to_markdown().replace("summary: 一句话结论\n", "").replace("scope: project\n", ""))
    assert plain.summary is None and not plain.project_wide


def test_module_scope_is_not_written_to_file():
    entry = Entry(id=new_ulid(), module="m.A", entity="E", kind="risk", content="内容", note_date="2026-10-19",
                  author="a", scope="module")
    assert "scope" not in entry.to_markdown()


def test_auto_summary_strips_kind_prefix_and_takes_first_sentence():
    assert auto_summary("决定：检索按相关度排序。原因是时间排序会漏老结论。") == "检索按相关度排序"
    assert auto_summary("更正（2026-10-19）：终端检索先挂起；执行完才算") == "终端检索先挂起"
    assert auto_summary("没有句号" + "长" * 80).endswith("…")


# ---- 写作提示 ----

def test_label_prefix_no_longer_hides_changelog_style():
    hints = content_hints("决定：新增了领取记录表，调整了按钮状态。", 600, "decision")
    assert len(hints) == 1 and "变更记录" in hints[0]


def test_decision_without_tradeoff_is_hinted():
    hints = content_hints("决定：检索结果按模块分组展示，结论放在前面，风格统一。", 600, "decision")
    assert any("为什么这样选" in h for h in hints)
    assert content_hints("决定：按模块分组展示，因为跨模块混排时找不到重点。", 600, "decision") == []


def test_verify_hint_only_for_conclusion_and_correction():
    assert verify_hint("conclusion", None) and verify_hint("correction", "")
    assert verify_hint("decision", None) is None and verify_hint("conclusion", "跑测试") is None


def test_record_without_summary_gets_generated_title_hint(svc):
    result = write(svc, aliases=["领奖"], verify="快速连点只发一次奖")
    assert any("没填 summary" in h and "拼图奖励重复发放的根因是领取按钮没有防连点" in h for h in result["hints"])


def test_summary_and_verify_are_searchable_and_returned(svc):
    written = write(svc, summary="红点不消失的根因", verify="切后台再回来红点消失", aliases=["领奖"])
    found = svc.search(module="gameplay.Jigsaw", query="红点")
    item = found["items"][0]
    assert item["id"] == written["id"]
    assert item["summary"] == "红点不消失的根因" and item["verify"] == "切后台再回来红点消失"


def test_invalid_scope_is_rejected_with_code(svc):
    result = svc.record("gameplay.Jigsaw", "Reward", "risk", CONTENT, scope="global")
    assert result["ok"] is False and result["code"] == "scope_invalid"


def test_draft_overwrite_keeps_summary_verify_and_scope(svc):
    first = write(svc, kind="risk", summary="标题", verify="验证办法", scope="project")
    again = svc.record("gameplay.Jigsaw", "Reward", "risk", CONTENT + "补充一句。", draft_id=first["draft_id"])
    entry = svc.index.find(again["id"])
    assert (entry.summary, entry.verify, entry.scope) == ("标题", "验证办法", "project")
    moved = svc.record("gameplay.Jigsaw", "Reward", "risk", CONTENT, draft_id=again["draft_id"], scope="module")
    assert svc.index.find(moved["id"]).scope is None


def test_secret_in_summary_is_rejected(svc):
    result = svc.record("gameplay.Jigsaw", "Reward", "risk", CONTENT, summary='api_key = "sk-abcdef1234567890XYZ"')
    assert result["ok"] is False and result["code"] == "secret"


# ---- 对话内去重 ----

def test_second_search_in_same_conversation_returns_titles_only(svc):
    written = write(svc, summary="领奖重复的根因")
    first = svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    assert first["items"][0]["content"] and "seen_hint" not in first
    second = svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    row = second["items"][0]
    assert row["id"] == written["id"] and row["seen"] is True and row["summary"] == "领奖重复的根因"
    assert "content" not in row and "seen_hint" in second


def test_field_hints_are_given_once_per_conversation(svc):
    write(svc)
    write(svc, entity="Share", kind="feature", content="用户要求：完成拼图后弹出分享面板。")
    first = svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    assert "features_hint" in first
    second = svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    assert "features_hint" not in second and "seen_hint" in second
    assert "seen_hint" in svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    seen.clear(svc.config.cache_dir, "c1")
    assert "features_hint" in svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    assert "features_hint" in svc.search(module="gameplay.Jigsaw")


def test_full_flag_and_other_conversations_get_full_text(svc):
    write(svc)
    svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    assert "content" in svc.search(module="gameplay.Jigsaw", source_conversation="c1", full=True)["items"][0]
    assert "content" in svc.search(module="gameplay.Jigsaw", source_conversation="c2")["items"][0]
    assert "content" in svc.search(module="gameplay.Jigsaw")["items"][0]


def test_collapsed_row_uses_generated_title_and_keeps_stale_flag(svc):
    write(svc, content="决定：领取按钮加防连点。原因是断线重连会重放请求。", kind="decision")
    svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    row = svc.search(module="gameplay.Jigsaw", source_conversation="c1")["items"][0]
    assert row["summary"] == "领取按钮加防连点" and "stale" in row


def test_cli_search_claims_conversation_from_hook_handoff(project):
    cli = MemoryService(project, source="cli")
    try:
        write(cli)
        cache = cli.config.cache_dir
        seen.note_handoff(cache, "conv-x", ["gameplay.jigsaw"])
        assert "content" in cli.search(module="gameplay.Jigsaw")["items"][0]
        assert cli.search(module="gameplay.Jigsaw")["items"][0].get("seen") is True
        # 登记的是别的模块时不认领
        (cache / seen.SEEN_DIR / seen.HANDOFF_FILE).unlink()
        seen.note_handoff(cache, "conv-y", ["economy.shop"])
        assert "content" in cli.search(module="gameplay.Jigsaw")["items"][0]
        assert "content" in cli.search(module="gameplay.Jigsaw")["items"][0]
    finally:
        cli.close()


def test_handoff_expires_and_global_search_only_claims_unscoped(tmp_path, monkeypatch):
    seen.note_handoff(tmp_path, "c1", [])
    assert seen.claim_handoff(tmp_path, None) == "c1"
    assert seen.claim_handoff(tmp_path, "gameplay.Jigsaw") is None
    later = time.time() + seen.HANDOFF_WINDOW + 1
    monkeypatch.setattr(seen.time, "time", lambda: later)
    assert seen.claim_handoff(tmp_path, None) is None


def test_handoff_wildcard_claims_any_module_for_variable_cli_search(project):
    """Shell 里 --module $m 解析不出时登记 *，命令行按真实模块名仍能折叠重复全文。"""
    cli = MemoryService(project, source="cli")
    try:
        write(cli)
        cache = cli.config.cache_dir
        seen.note_handoff(cache, "conv-var", [seen.HANDOFF_ANY])
        assert "content" in cli.search(module="gameplay.Jigsaw")["items"][0]
        assert cli.search(module="gameplay.Jigsaw")["items"][0].get("seen") is True
    finally:
        cli.close()


def test_search_event_records_collapsed_ids(svc):
    write(svc)
    svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    svc.search(module="gameplay.Jigsaw", source_conversation="c1")
    lines = (svc.config.cache_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    searches = [json.loads(line) for line in lines if '"search"' in line]
    assert searches[-1]["collapsed"] == searches[-1]["ids"] and not searches[-2].get("collapsed")


# ---- 闸门：标题、全项目级坑、压缩后重置、终端交接、结束提醒 ----

def _entry(root: Path, module: str, kind: str, content: str, extra: str = "") -> str:
    entry_id = new_ulid()
    folder = root / ".memory" / "entries" / module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{entry_id}.md").write_text(
        f"---\nid: {entry_id}\nmodule: {module}\nentity: Reward\nkind: {kind}\nstatus: active\nauthor: a\n"
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


def test_digest_shows_titles_without_duplicate_kind_prefix(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "decision", "决定：领奖走服务端校验。因为客户端可被篡改。")
    text = _read(gate_root, "src/Jigsaw/Board.cs")
    assert "决定｜Reward｜2026-10-01：领奖走服务端校验" in text and "决定：决定" not in text


def test_project_pitfalls_are_attached_once_per_conversation(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "conclusion", "拼图结论：奖励按关卡发。")
    risk = _entry(gate_root, "economy.Shop", "risk", "风险：PowerShell 5 改中文文件会坏编码。", "scope: project\n")
    first = _read(gate_root, "src/Jigsaw/Board.cs")
    assert "全项目通用的坑" in first and "economy.Shop/Reward" in first
    denied = handle("pre-tool", {"conversation_id": "c1", "tool_name": "Write",
                                 "tool_input": {"file_path": str(gate_root / "src/Jigsaw/Board.cs")}}, gate_root)
    assert denied["permission"] == "deny" and "全项目通用" not in denied["user_message"]
    state = json.loads(next((Config.load(gate_root).cache_dir / "sessions").glob("c1.json")).read_text("utf-8"))
    assert state["project_shown"] == [risk]
    assert "全项目通用的坑" in _read(gate_root, "src/Jigsaw/Board.cs", conv="c2")


def test_module_without_memories_still_gets_project_pitfalls(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "exclusion", "排除：不要在客户端去重。", "scope: project\n")
    text = _read(gate_root, "src/Shop/Shop.cs")
    assert "该模块还没有记忆" in text and "不要在客户端去重" in text


def test_guard_lists_project_pitfalls_when_not_yet_shown(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "conclusion", "拼图结论：奖励按关卡发。")
    _entry(gate_root, "economy.Shop", "risk", "风险：PowerShell 5 改中文文件会坏编码。", "scope: project\n")
    denied = handle("pre-tool", {"conversation_id": "c1", "tool_name": "Write",
                                 "tool_input": {"file_path": str(gate_root / "src/Jigsaw/Board.cs")}}, gate_root)
    assert "全项目通用的坑" in denied["user_message"] and "PowerShell 5 改中文文件会坏编码" in denied["user_message"]


def _session(root: Path, conv: str = "c1") -> dict:
    return json.loads((Config.load(root).cache_dir / "sessions" / f"{conv}.json").read_text("utf-8"))


def test_project_scan_stops_once_nothing_left_to_show(gate_root, monkeypatch):
    from pmem.hooks import gate as gate_mod

    scans = []
    original = gate_mod.Gate.project_entries
    monkeypatch.setattr(gate_mod.Gate, "project_entries", lambda self: scans.append(1) or original(self))
    _read(gate_root, "src/Shop/Shop.cs")
    _read(gate_root, "src/Shop/Shop.cs")
    _read(gate_root, "src/Jigsaw/Board.cs")
    assert len(scans) == 1 and _session(gate_root)["project_done"] is True
    _entry(gate_root, "gameplay.Jigsaw", "risk", "风险：改中文文件会坏编码。", "scope: project\n")
    handle("compact", {"conversation_id": "c1"}, gate_root)
    assert _session(gate_root)["project_done"] is False
    assert "改中文文件会坏编码" in _read(gate_root, "src/Shop/Shop.cs")
    _read(gate_root, "src/Shop/Shop.cs")
    assert len(scans) == 2


def test_project_pitfall_of_own_module_waits_for_other_modules(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "risk", "风险：改中文文件会坏编码。", "scope: project\n")
    assert "全项目通用" not in _read(gate_root, "src/Jigsaw/Board.cs")
    assert _session(gate_root)["project_done"] is False
    assert "改中文文件会坏编码" in _read(gate_root, "src/Shop/Shop.cs")
    assert _session(gate_root)["project_done"] is True


def test_compact_clears_seen_ledger(gate_root):
    cache = Config.load(gate_root).cache_dir
    seen.add(cache, "c1", ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"])
    handle("compact", {"conversation_id": "c1"}, gate_root)
    assert seen.load(cache, "c1") == set()


def test_shell_pmem_search_registers_handoff(gate_root):
    _entry(gate_root, "gameplay.Jigsaw", "conclusion", "拼图结论：奖励按关卡发。")
    shell = {"conversation_id": "c7", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module gameplay.Jigsaw --brief", "cwd": ""}}
    handle("pre-tool", shell, gate_root)
    assert seen.claim_handoff(Config.load(gate_root).cache_dir, "gameplay.Jigsaw") == "c7"


def test_shell_variable_module_registers_wildcard_handoff(gate_root):
    shell = {"conversation_id": "c8", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module $m --brief", "cwd": ""}}
    handle("pre-tool", shell, gate_root)
    assert seen.claim_handoff(Config.load(gate_root).cache_dir, "gameplay.Jigsaw") == "c8"


def test_stop_reminder_asks_for_feature_record_plus_lessons(gate_root):
    handle("edited", {"conversation_id": "c1", "file_path": str(gate_root / "src/Shop/Shop.cs")}, gate_root)
    message = handle("stop", {"conversation_id": "c1", "status": "completed"}, gate_root)["followup_message"]
    assert message.startswith("[pmem]") and "kind=feature" in message and "exclusion" in message
    assert "【pmem修改】" in message and "无需记录：" in message and "不写“改了哪个方法”" in message


# ---- 度量 ----

def test_repeats_counts_full_repeats_and_collapsed():
    events = [
        {"type": "search", "ok": True, "conv": "c1", "ts": 1, "ids": ["a", "b"]},
        {"type": "search", "ok": True, "conv": "c1", "ts": 2, "ids": ["a", "c"]},
        {"type": "search", "ok": True, "conv": "c1", "ts": 3, "ids": ["b", "c"], "collapsed": ["b", "c"]},
        {"type": "search", "ok": True, "conv": "c2", "ts": 4, "ids": ["a"]},
        {"type": "search", "ok": True, "ts": 5, "ids": ["a"]},
    ]
    assert _repeats(events) == {"items": 7, "repeated": 1, "collapsed": 2, "compactions": 0, "inferred": 0,
                                "unsplit": 1}


def test_repeats_after_compaction_are_not_counted():
    """压缩清空了“已给过”，再给全文是有意的；没有压缩事件的旧日志按同一模块的读代码摘要重复出现推断。"""
    events = [
        {"type": "search", "ok": True, "conv": "c1", "ts": 1, "ids": ["a"]},
        {"type": "compact", "conv": "c1", "ts": 2},
        {"type": "search", "ok": True, "conv": "c1", "ts": 3, "ids": ["a"]},
        {"type": "digest", "conv": "c2", "ts": 4, "module": "m.A", "ids": ["x"]},
        {"type": "search", "ok": True, "conv": "c2", "ts": 5, "ids": ["b"]},
        {"type": "digest", "conv": "c2", "ts": 6, "module": "m.A", "ids": ["x"]},
        {"type": "search", "ok": True, "conv": "c2", "ts": 7, "ids": ["b"]},
        # 只给了全项目通用的坑时不记已看过，同一模块再给摘要不代表压缩过
        {"type": "digest", "conv": "c3", "ts": 8, "module": "m.A", "ids": []},
        {"type": "search", "ok": True, "conv": "c3", "ts": 9, "ids": ["c"]},
        {"type": "digest", "conv": "c3", "ts": 10, "module": "m.A", "ids": ["x"]},
        {"type": "search", "ok": True, "conv": "c3", "ts": 11, "ids": ["c"]},
        # 查过某模块也会记已看过，之后又出现它的摘要同样说明压缩过
        {"type": "mcp_search", "conv": "c4", "ts": 12, "module": "m.B"},
        {"type": "search", "ok": True, "conv": "c4", "ts": 12.5, "ids": ["d"]},
        {"type": "digest", "conv": "c4", "ts": 13, "module": "m.B", "ids": ["y"]},
        {"type": "search", "ok": True, "conv": "c4", "ts": 14, "ids": ["d"]},
    ]
    assert _repeats(events) == {"items": 8, "repeated": 1, "collapsed": 0, "compactions": 3, "inferred": 2,
                                "unsplit": 4}


def test_pitfall_share_and_render_warns_when_low():
    now = time.time()
    old = Entry(id=new_ulid(int((now - 100 * 86400) * 1000)), module="m.A", entity="E", kind="risk", content="x",
                note_date="2026-01-01", author="a")
    new = [Entry(id=new_ulid(), module="m.A", entity="E", kind=k, content="x", note_date="2026-10-19", author="a")
           for k in ("decision", "decision", "decision", "exclusion")]
    share = _pitfall_share([old, *new], now - 30 * 86400)
    assert share == {"new": 4, "new_pitfalls": 1, "old": 1, "old_pitfalls": 1}
    lines = _render_quality(share, {"items": 10, "repeated": 4, "collapsed": 3})
    assert "25%" in lines[0] and "偏低" in lines[0] and "4 条（40%）" in lines[1]


def test_health_flags_repeated_corrections_in_period():
    now = time.time()
    rows = [Entry(id=new_ulid(), module="m.A", entity="Enc", kind="correction", content="x", note_date="2026-10-19",
                  author="a") for _ in range(2)]
    rows.append(Entry(id=new_ulid(), module="m.A", entity="Other", kind="correction", content="x",
                      note_date="2026-10-19", author="a"))
    assert _repeat_corrections(rows, now - 86400) == [("m.A", "Enc", 2)]


def test_health_lists_existing_cross_module_supersedes():
    def entry(module, supersedes=()):
        return Entry(id=new_ulid(), module=module, entity="E", kind="correction", content="x",
                     note_date="2026-10-19", author="a", supersedes=list(supersedes))

    old, same = entry("m.B"), entry("m.A")
    cross, local = entry("m.A", [old.id]), entry("m.A", [same.id])
    assert _cross_module_supersedes([old, same, cross, local], {cross.id, local.id}) == [
        {"id": cross.id, "module": "m.A", "replaced": old.id, "replaced_module": "m.B"}]
    assert _cross_module_supersedes([old, cross], set()) == []
    assert reject_reason("", "supersede_cross_module") == "替代了别的模块的记忆"


# ---- 命令行简报 ----

def test_brief_marks_seen_rows_and_shows_verify():
    result = {"ok": True, "module": "gameplay.Jigsaw", "seen_hint": "标 seen 的 1 条……", "items": [
        {"id": "A", "entity": "Reward", "kind": "decision", "date": "2026-10-19", "summary": "标题一", "seen": True},
        {"id": "B", "entity": "Reward", "kind": "conclusion", "date": "2026-10-19", "content": "结论：正文。",
         "verify": "跑 test_reward", "scope": "project"},
    ]}
    text = render_brief("search", result)
    assert "（本对话已给过全文）标题一" in text and "（全项目）" in text and "验证：跑 test_reward" in text
    assert "结论（全项目）｜Reward｜2026-10-19｜B：正文。" in text and "提示：标 seen 的 1 条" in text
