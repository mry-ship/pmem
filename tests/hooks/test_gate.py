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
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "result_json": json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "gameplay.Jigsaw"})}
    handle("after-mcp", after, root)
    second = handle("pre-tool", payload, root)
    assert second["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"


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


def test_analysis_only_conversation_is_logged_but_not_reminded_by_default(make_project):
    root = make_project()
    assert _analysis_turn(root, "拼图奖励为什么会重复发放？") == {}
    assert _last_stop(root)["analyzed"] == ["gameplay.Jigsaw"]


def test_analysis_reminder_can_be_enabled(make_project):
    root = make_project()
    config = root / ".memory" / "config.yaml"
    text = config.read_text(encoding="utf-8").replace("mode: warn", "mode: warn, analysis_reminder: true")
    config.write_text(text, encoding="utf-8")
    first = _analysis_turn(root, "Why does the reward get granted twice?")
    assert "排查了 gameplay.Jigsaw" in first["followup_message"]
    assert _analysis_turn(root, "再看看") == {}


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
