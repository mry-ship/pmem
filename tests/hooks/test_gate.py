import json
from pathlib import Path

import pytest

from pmem.core.config import Config
from pmem.hooks.gate import cli_args, handle, shell_write_targets
from pmem.metrics.events import read_events

CONFIG = "project: {{ name: demo }}\nvcs: none\ngate: {{ mode: {mode} }}\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
ENTRY = """---
id: {id}
module: {module}
entity: Reward
kind: conclusion
status: active
author: a
note_date: '2026-10-01'
---
旧结论
"""


@pytest.fixture
def make_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))

    def build(mode="warn", with_memory=True) -> Path:
        root = tmp_path / "proj"
        (root / ".memory").mkdir(parents=True, exist_ok=True)
        (root / ".memory" / "config.yaml").write_text(CONFIG.format(mode=mode), encoding="utf-8")
        (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
        if with_memory:
            folder = root / ".memory" / "entries" / "gameplay.Jigsaw"
            folder.mkdir(parents=True, exist_ok=True)
            entry_id = "01JA7K3M2X9F4Q8W6ZB1C2D3E4"
            (folder / f"{entry_id}.md").write_text(ENTRY.format(id=entry_id, module="gameplay.Jigsaw"), "utf-8")
        return root

    return build


def write_payload(root: Path, rel: str, conv="c1") -> dict:
    return {
        "conversation_id": conv,
        "hook_event_name": "preToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(root / rel), "content": "x"},
    }


def search_payload(conv="c1", **args) -> dict:
    return {"conversation_id": conv, "hook_event_name": "beforeMCPExecution", "tool_name": "search_memory",
            "tool_input": json.dumps(args)}


def test_unmapped_path_is_allowed(make_project):
    root = make_project()
    assert handle("pre-tool", write_payload(root, "tools/x.py"), root)["permission"] == "allow"


def test_module_without_memories_is_allowed(make_project):
    root = make_project()
    assert handle("pre-tool", write_payload(root, "src/Shop/Shop.cs"), root)["permission"] == "allow"


def test_warn_denies_once_then_allows(make_project):
    root = make_project("warn")
    first = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert first["permission"] == "deny"
    assert 'search_memory(module="gameplay.Jigsaw")' in first["agent_message"]
    second = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert second["permission"] == "allow"


def test_block_denies_until_searched(make_project):
    root = make_project("block")
    for _ in range(2):
        assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    handle("before-mcp", search_payload(module="gameplay.jigsaw"), root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_block_is_the_default_mode(make_project):
    root = make_project()
    (root / ".memory" / "config.yaml").write_text("project: { name: demo }\nvcs: none\n", encoding="utf-8")
    for _ in range(2):
        assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_failed_search_still_unlocks_block(make_project):
    root = make_project("block")
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    failed = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
              "result_json": json.dumps({"ok": False, "error": "index unavailable"})}
    handle("after-mcp", failed, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_block_message_explains_fallbacks(make_project):
    root = make_project("block")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["agent_message"]
    assert "pmem search --module gameplay.Jigsaw" in message
    assert "跳过记忆" in message


def test_search_by_path_counts_as_searched(make_project):
    root = make_project("block")
    handle("before-mcp", search_payload(path="src/Jigsaw/Other.cs"), root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_successful_search_result_counts_as_searched(make_project):
    root = make_project("block")
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "items": []})}
    handle("after-mcp", after, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_deny_message_shown_to_agent_is_actionable(make_project):
    root = make_project("warn")
    verdict = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert 'search_memory(module="gameplay.Jigsaw")' in verdict["user_message"]
    assert "重试" in verdict["user_message"]


def test_off_mode_allows(make_project):
    root = make_project("off")
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_conversations_do_not_share_state(make_project):
    root = make_project("block")
    handle("before-mcp", search_payload(conv="c1", module="gameplay.Jigsaw"), root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/B.cs", conv="c2"), root)["permission"] == "deny"


def test_missing_conversation_id_never_blocks(make_project):
    root = make_project("block")
    payload = write_payload(root, "src/Jigsaw/Board.cs", conv="")
    assert handle("pre-tool", payload, root)["permission"] == "allow"


def test_skip_marker_in_prompt_disables_gate(make_project):
    root = make_project("block")
    handle("prompt", {"conversation_id": "c1", "prompt": "这次跳过记忆，直接改"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_compact_resets_searched(make_project):
    root = make_project("block")
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    handle("compact", {"conversation_id": "c1"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_shell_write_is_gated(make_project):
    root = make_project("block")
    payload = {"conversation_id": "c1", "tool_name": "Shell",
               "tool_input": {"command": "echo hi > src/Jigsaw/Board.cs", "cwd": ""}}
    assert handle("pre-tool", payload, root)["permission"] == "deny"
    payload["tool_input"]["command"] = "git status"
    assert handle("pre-tool", payload, root)["permission"] == "allow"


@pytest.mark.parametrize(
    ("command", "targets"),
    [
        ("echo hi > a.txt", ["a.txt"]),
        ("cat x >> logs/b.log", ["logs/b.log"]),
        ("Set-Content -Path src/A.cs -Value 1", ["src/A.cs"]),
        ("'x' | Out-File src/B.cs", ["src/B.cs"]),
        ("sed -i 's/a/b/' src/C.cs", ["src/C.cs"]),
        ("ls | tee out.txt", ["out.txt"]),
        ("Remove-Item src/D.cs", ["src/D.cs"]),
        ("rm -f src/E.cs", ["src/E.cs"]),
        ("git status 2>&1", []),
        ("cmd > $null", []),
    ],
)
def test_shell_write_targets(command, targets):
    assert shell_write_targets(command) == targets


def test_record_injection_adds_conversation_and_draft(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": "x"}}
    first = handle("pre-tool", payload, root)
    assert first["updated_input"]["source_conversation"] == "c1"
    assert "draft_id" not in first["updated_input"]
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "gameplay.Jigsaw", "entity": "Reward"}
    after = {"conversation_id": "c1", "tool_name": "record_memory", "result_json": json.dumps(response)}
    handle("after-mcp", after, root)
    second = handle("pre-tool", payload, root)
    assert second["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"
    other = {**payload, "tool_input": {**payload["tool_input"], "entity": "Config"}}
    assert "draft_id" not in handle("pre-tool", other, root)["updated_input"]
    same = {**payload, "tool_input": {**payload["tool_input"], "entity": "reward"}}
    assert handle("pre-tool", same, root)["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"


def test_after_mcp_reads_module_from_nested_response_not_input(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop", "entity": "Price",
                "similar": [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "entity": "Price"}]}
    wrapped = json.dumps({"content": [{"type": "text", "text": json.dumps(response, ensure_ascii=False)}]})
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "tool_input": json.dumps({"module": "gameplay.Jigsaw", "entity": "Price"}), "result_json": wrapped}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}
    failed = {**after, "result_json": json.dumps({"ok": False, "error": "x", "module": "gameplay.Jigsaw"})}
    handle("after-mcp", {**failed, "conversation_id": "c2"}, root)
    handle("edited", {"conversation_id": "c2", "file_path": str(root / "src/Jigsaw/Board.cs")}, root)
    assert "gameplay.Jigsaw" in handle("stop", {"conversation_id": "c2", "status": "completed"}, root)["followup_message"]


def test_stop_reminds_once_for_edited_modules_without_record(make_project):
    root = make_project()
    edit = {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}
    handle("edited", edit, root)
    first = handle("stop", {"conversation_id": "c1", "status": "completed"}, root)
    assert "economy.Shop" in first["followup_message"]
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_stop_is_quiet_when_module_was_recorded(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "result_json": json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop"})}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_stop_is_quiet_when_aborted(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    assert handle("stop", {"conversation_id": "c1", "status": "aborted"}, root) == {}


@pytest.mark.parametrize(
    ("command", "args"),
    [
        ("pmem search --module gameplay.Jigsaw", [{"module": "gameplay.Jigsaw"}]),
        ("cd proj; uv run pmem search --path src/a.cs", [{"path": "src/a.cs"}]),
        (r"C:\bin\pmem.exe search 奖励", [{}]),
        ("pmem search --module a.B; pmem search --module c.D", [{"module": "a.B"}, {"module": "c.D"}]),
        ("uv run --extra embed pmem search --module a.B; git add -A", [{"module": "a.B"}]),
        ("python -m pmem search --path x.cs", [{"path": "x.cs"}]),
        ("pmem list", []),
        ("echo pmem search", []),
    ],
)
def test_cli_search_args(command, args):
    assert cli_args(command, "search") == args


def test_cli_record_in_shell_silences_stop_reminder(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem record --module economy.Shop --entity Price --kind risk "
                                       "--content-file note.txt", "cwd": ""}}
    assert handle("pre-tool", shell, root)["permission"] == "allow"
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_every_cli_record_in_one_command_counts(make_project):
    root = make_project()
    for path in ("src/Shop/Shop.cs", "src/Jigsaw/Board.cs"):
        handle("edited", {"conversation_id": "c1", "file_path": str(root / path)}, root)
    command = ("$t=$env:TEMP; uv run pmem record --module economy.Shop --entity A --kind risk --content-file a.md; "
               "uv run pmem record --module gameplay.Jigsaw --entity B --kind risk --content-file b.md")
    shell = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"command": command, "cwd": ""}}
    assert handle("pre-tool", shell, root)["permission"] == "allow"
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_cli_record_is_logged_for_report(make_project):
    root = make_project()
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem record --module economy.Shop --entity Price --kind risk "
                                       "--content-file note.txt", "cwd": ""}}
    handle("pre-tool", shell, root)
    events = list(read_events(Config.load(root).cache_dir))
    assert [(e["type"], e["module"], e["conv"]) for e in events] == [("record_call", "economy.Shop", "c1")]


def test_record_injection_adds_files_edited_in_module(make_project):
    root = make_project()
    for path in ("src/Shop/Shop.cs", "src/Jigsaw/Board.cs", "src/Shop/Price.cs"):
        handle("edited", {"conversation_id": "c1", "file_path": str(root / path)}, root)
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "economy.Shop", "entity": "Price", "kind": "risk", "content": "x"}}
    assert handle("pre-tool", payload, root)["updated_input"]["anchors"] == ["src/Shop/Shop.cs", "src/Shop/Price.cs"]
    payload["tool_input"]["anchors"] = ["src/Shop/Shop.cs#Buy"]
    assert handle("pre-tool", payload, root)["updated_input"]["anchors"] == ["src/Shop/Shop.cs#Buy"]


def _analysis_turn(root: Path, prompt: str, conv="c1") -> dict:
    handle("prompt", {"conversation_id": conv, "prompt": prompt}, root)
    handle("before-mcp", search_payload(conv=conv, module="gameplay.Jigsaw"), root)
    return handle("stop", {"conversation_id": conv, "status": "completed"}, root)


def _last_stop(root: Path) -> dict:
    return [e for e in read_events(Config.load(root).cache_dir) if e["type"] == "stop"][-1]


def test_consulted_only_conversation_is_reminded_once(make_project):
    root = make_project()
    first = _analysis_turn(root, "拼图奖励为什么会重复发放？")
    assert "查了 gameplay.Jigsaw 的记忆" in first["followup_message"]
    assert "无需记录" in first["followup_message"]
    assert _last_stop(root)["analyzed"] == ["gameplay.Jigsaw"]
    assert _analysis_turn(root, "再看看") == {}


def test_consulted_reminder_does_not_need_analysis_wording(make_project):
    root = make_project()
    assert "gameplay.Jigsaw" in _analysis_turn(root, "给拼图加一个新关卡")["followup_message"]


def test_lookups_during_coding_are_not_reminded(make_project):
    root = make_project()
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "result_json": json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop"})}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_consulted_reminder_can_be_disabled(make_project):
    root = make_project()
    config = root / ".memory" / "config.yaml"
    text = config.read_text(encoding="utf-8").replace("mode: warn", "mode: warn, analysis_reminder: false")
    config.write_text(text, encoding="utf-8")
    assert _analysis_turn(root, "Why does the reward get granted twice?") == {}
    assert _last_stop(root)["analyzed"] == ["gameplay.Jigsaw"]


def test_non_analysis_or_recorded_conversations_are_not_counted(make_project):
    root = make_project()
    _analysis_turn(root, "给拼图加一个新关卡", conv="plain")
    assert "analyzed" not in _last_stop(root)
    handle("prompt", {"conversation_id": "rec", "prompt": "排查一下拼图报错"}, root)
    handle("before-mcp", search_payload(conv="rec", module="gameplay.Jigsaw"), root)
    shell = {"conversation_id": "rec", "tool_name": "Shell",
             "tool_input": {"command": "pmem record --module gameplay.Jigsaw --entity A --kind risk --content-file a.md"}}
    handle("pre-tool", shell, root)
    handle("stop", {"conversation_id": "rec", "status": "completed"}, root)
    assert "analyzed" not in _last_stop(root)


def test_cli_search_in_shell_counts_as_searched(make_project):
    root = make_project("block")
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module gameplay.Jigsaw", "cwd": ""}}
    assert handle("pre-tool", shell, root)["permission"] == "allow"
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_search_injection_adds_conversation(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": {"module": "gameplay.Jigsaw"}}
    assert handle("pre-tool", payload, root)["updated_input"]["source_conversation"] == "c1"


@pytest.mark.parametrize("tool_input", [{"module": "system.AdChase", "query": "插屏"}, {"query": "插屏"}])
def test_search_injection_skips_other_memory_servers(make_project, tool_input):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": tool_input}
    assert "updated_input" not in handle("pre-tool", payload, root)


def test_events_are_logged_for_report(make_project):
    root = make_project("warn")
    handle("prompt", {"conversation_id": "c1", "prompt": "修一下", "composer_mode": "agent"}, root)
    handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw",
                                        "items": [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "kind": "conclusion"}]})}
    handle("after-mcp", after, root)
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Jigsaw/Board.cs")}, root)
    handle("stop", {"conversation_id": "c1", "status": "completed", "input_tokens": 1000, "output_tokens": 50,
                    "transcript_path": "t.jsonl"}, root)
    events = list(read_events(Config.load(root).cache_dir))
    assert [e["type"] for e in events] == ["prompt", "gate", "search_call", "mcp_search", "edit", "stop"]
    assert all(e["conv"] == "c1" for e in events)
    assert events[3]["ids"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    stop = events[-1]
    assert stop["input_tokens"] == 1000 and stop["returned"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    assert stop["nudged"] == ["gameplay.Jigsaw"]


# ---- 提问审查 ----

def read_payload(root: Path, rel: str, conv="c1") -> dict:
    return {"conversation_id": conv, "hook_event_name": "postToolUse", "tool_name": "Read",
            "tool_input": {"file_path": str(root / rel)}}


def add_entry(root: Path, entry_id: str, kind: str, content: str, day: str, entity="Reward", supersedes="",
              module="gameplay.Jigsaw"):
    folder = root / ".memory" / "entries" / module
    folder.mkdir(parents=True, exist_ok=True)
    extra = f"supersedes: [{supersedes}]\n" if supersedes else ""
    text = (f"---\nid: {entry_id}\nmodule: {module}\nentity: {entity}\nkind: {kind}\nstatus: active\n"
            f"author: a\nnote_date: '{day}'\n{extra}---\n{content}\n")
    (folder / f"{entry_id}.md").write_text(text, encoding="utf-8")


def transcript(tmp_path: Path, *user_texts: str) -> str:
    path = tmp_path / "t.jsonl"
    lines = []
    for text in user_texts:
        lines.append({"role": "user", "message": {"content": [{"type": "text", "text": text}]}})
        lines.append({"role": "assistant", "message": {"content": [{"type": "text", "text": "好的"}]}})
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8")
    return str(path)


def stop_payload(path: str | None = None, conv="c1", **extra) -> dict:
    return {"conversation_id": conv, "status": "completed", "transcript_path": path, **extra}


def test_reading_module_code_attaches_digest_once(make_project):
    root = make_project("block")
    first = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    assert "src/Jigsaw/Board.cs 属于 gameplay.Jigsaw" in first["additional_context"]
    assert "旧结论" in first["additional_context"]
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Other.cs"), root) == {}
    # 摘要不等于检索：改代码仍要先查
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


@pytest.mark.parametrize("rel", ["src/Shop/Shop.cs", "src/Jigsaw/README.md", "tools/x.py"])
def test_no_digest_without_memories_or_for_ignored_files(make_project, rel):
    root = make_project()
    assert handle("post-tool", read_payload(root, rel), root) == {}


def test_digest_puts_exclusions_first_and_hides_superseded(make_project):
    root = make_project(with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "conclusion", "最新的普通结论", "2026-10-05")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "exclusion", "不要在客户端去重", "2026-09-01", entity="Dedup")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A3", "conclusion", "已被推翻的旧说法", "2026-08-01", entity="Old")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A4", "correction", "更正后的说法", "2026-09-02", entity="Old",
              supersedes="01JA7K3M2X9F4Q8W6ZB1C2D3A3")
    text = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    assert "有 3 条现行研发记忆" in text
    assert text.index("排除项｜Dedup") < text.index("更正｜Old") < text.index("结论｜Reward")
    assert "已被推翻" not in text


def test_question_about_module_is_reviewed_at_stop(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<timestamp>x</timestamp>\n<user_query>\nJigsaw 的奖励为什么会重复发？\n</user_query>")
    result = handle("stop", stop_payload(path), root)
    assert "你的问题涉及 gameplay.Jigsaw" in result["followup_message"]
    assert "已核对记忆" in result["followup_message"]
    assert _last_stop(root)["review"] == ["gameplay.Jigsaw"]
    # 同一模块一个对话只追问一次
    assert handle("stop", stop_payload(path), root) == {}


def test_question_review_uses_paths_aliases_and_ignores_attachments(make_project, tmp_path):
    root = make_project()
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3S1", "risk", "商店价格缓存的风险", "2026-10-01", module="economy.Shop")
    text = "<attached_files>economy.Shop 的代码</attached_files>\n<user_query>看下 src/Jigsaw/Board.cs</user_query>"
    result = handle("stop", stop_payload(transcript(tmp_path, text)), root)
    assert "gameplay.Jigsaw" in result["followup_message"]
    assert "economy.Shop" not in result["followup_message"]


def test_no_review_when_memories_were_seen(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    assert handle("stop", stop_payload(path), root) == {}
    handle("before-mcp", search_payload(conv="c2", module="gameplay.Jigsaw"), root)
    result = handle("stop", stop_payload(path, conv="c2"), root)
    assert "你的问题涉及" not in result.get("followup_message", "")


def test_global_search_results_count_as_reviewed(make_project, tmp_path):
    root = make_project()
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": None, "items": [
                 {"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "module": "gameplay.Jigsaw", "kind": "conclusion"}]})}
    handle("after-mcp", after, root)
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    assert "你的问题涉及" not in handle("stop", stop_payload(path), root).get("followup_message", "")


@pytest.mark.parametrize("extra", [{"loop_count": 1}, {"stop_hook_active": True}])
def test_followup_turns_do_not_trigger_more_followups(make_project, tmp_path, extra):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    assert handle("stop", stop_payload(path, **extra), root) == {}
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(path), root)["followup_message"]


def test_pmem_followup_message_is_not_treated_as_a_question(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>[pmem] 本轮修改了 gameplay.Jigsaw，但还没有写研发记忆</user_query>")
    assert handle("stop", stop_payload(path), root) == {}


def test_review_falls_back_to_prompt_without_transcript(make_project):
    root = make_project()
    handle("prompt", {"conversation_id": "c1", "prompt": "check src/Jigsaw/Board.cs please"}, root)
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(None), root)["followup_message"]


def test_review_combines_with_write_reminder(make_project, tmp_path):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复，顺便改下商店</user_query>")
    message = handle("stop", stop_payload(path), root)["followup_message"]
    assert "你的问题涉及 gameplay.Jigsaw" in message and "本轮修改了 economy.Shop" in message


def test_review_can_be_disabled_and_respects_skip(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    handle("prompt", {"conversation_id": "skip", "prompt": "跳过记忆，看下 Jigsaw"}, root)
    assert handle("stop", stop_payload(path, conv="skip"), root) == {}
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs", conv="skip"), root) == {}
    config = root / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace(
        "mode: warn", "mode: warn, question_review: false, read_digest: false"), encoding="utf-8")
    assert handle("stop", stop_payload(path), root) == {}
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root) == {}


def test_compaction_forgets_seen_memories(make_project):
    root = make_project()
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    handle("compact", {"conversation_id": "c1"}, root)
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)


def test_prompt_context_agents_get_digest_at_prompt_time(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "prompt": "拼图 Jigsaw 的奖励怎么发", "prompt_context": True}
    result = handle("prompt", payload, root)
    assert result["continue"] is True and "你的问题提到了 gameplay.Jigsaw" in result["additional_context"]
    assert "additional_context" not in handle("prompt", {"conversation_id": "c2", "prompt": "Jigsaw"}, root)
