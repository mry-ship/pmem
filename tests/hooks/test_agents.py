import io
import json
import sys
from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.hooks.agents import normalize, patch_files, render
from pmem.hooks.gate import handle

CONFIG = "project: { name: demo }\nvcs: none\ngate: { mode: block }\n"
MODULES = """
categories: { gameplay: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
"""
ENTRY = """---
id: 01JA7K3M2X9F4Q8W6ZB1C2D3E4
module: gameplay.Jigsaw
entity: Reward
kind: conclusion
author: a
note_date: '2026-10-01'
---
旧结论
"""


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    folder = root / ".memory" / "entries" / "gameplay.Jigsaw"
    folder.mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(ENTRY, encoding="utf-8")
    return root


def run(agent: str, event: str, payload: dict, root: Path) -> dict:
    return render(agent, event, handle(event, normalize(agent, payload), root))


def claude_edit(root: Path, rel: str, session="s1") -> dict:
    return {"session_id": session, "cwd": str(root), "hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(root / rel), "old_string": "a", "new_string": "b"}}


def test_patch_files_lists_every_touched_file():
    patch = ("*** Begin Patch\n*** Update File: src/a.py\n@@\n-x\n+y\n*** Add File: src/b.py\n+z\n"
             "*** Delete File: src/c.py\n*** Update File: src/d.py\n*** Move to: src/e.py\n*** End Patch")
    assert patch_files(patch) == ["src/a.py", "src/b.py", "src/c.py", "src/d.py", "src/e.py"]


def test_claude_edit_is_denied_until_module_searched(root):
    denied = run("claude", "pre-tool", claude_edit(root, "src/Jigsaw/Board.cs"), root)
    output = denied["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert 'search_memory(module="gameplay.Jigsaw")' in output["permissionDecisionReason"]

    search = {"session_id": "s1", "tool_name": "mcp__pmem__search_memory",
              "tool_input": {"module": "gameplay.Jigsaw", "query": "奖励"}}
    marked = run("claude", "pre-tool", search, root)
    # Claude Code 的 updatedInput 整体替换原参数，必须带上原有字段
    assert marked["hookSpecificOutput"]["updatedInput"] == {"module": "gameplay.Jigsaw", "query": "奖励",
                                                            "source_conversation": "s1"}
    assert run("claude", "pre-tool", claude_edit(root, "src/Jigsaw/Board.cs"), root)  # 还没返回结果
    result = {"content": [{"type": "text", "text": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "items": []})}]}
    run("claude", "post-tool", {**search, "tool_response": result}, root)
    assert run("claude", "pre-tool", claude_edit(root, "src/Jigsaw/Board.cs"), root) == {}


def test_plain_allow_is_not_forwarded_so_agent_keeps_its_own_permission_prompts(root):
    bash = {"session_id": "s1", "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": "ls src"}}
    assert run("claude", "pre-tool", bash, root) == {}
    assert run("codex", "pre-tool", bash, root) == {}


def test_bash_redirect_into_guarded_module_is_denied(root):
    bash = {"session_id": "s1", "cwd": str(root), "tool_name": "Bash",
            "tool_input": {"command": "echo x > src/Jigsaw/Board.cs"}}
    assert run("codex", "pre-tool", bash, root)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_codex_patch_touching_any_guarded_file_is_denied(root):
    patch = "*** Begin Patch\n*** Update File: tools/x.py\n*** Update File: src/Jigsaw/Board.cs\n*** End Patch"
    payload = {"session_id": "s2", "cwd": str(root), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    assert run("codex", "pre-tool", payload, root)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_cli_search_in_bash_unlocks_module(root):
    bash = {"session_id": "s3", "cwd": str(root), "tool_name": "Bash",
            "tool_input": {"command": "pmem search --module gameplay.Jigsaw 奖励"}}
    run("claude", "pre-tool", bash, root)
    assert run("claude", "pre-tool", claude_edit(root, "src/Jigsaw/Board.cs", "s3"), root) != {}
    run("claude", "post-tool", {**bash, "tool_response": {"stdout": "gameplay.Jigsaw：1 条", "stderr": ""}}, root)
    assert run("claude", "pre-tool", claude_edit(root, "src/Jigsaw/Board.cs", "s3"), root) == {}


def test_stop_reminder_after_edit_blocks_so_every_agent_version_continues(root):
    for agent, session in (("claude", "s4"), ("codex", "s5")):
        run(agent, "pre-tool", {"session_id": session, "tool_name": "mcp__pmem__search_memory",
                                "tool_input": {"module": "gameplay.Jigsaw"}}, root)
        edit = claude_edit(root, "src/Jigsaw/Board.cs", session)
        if agent == "codex":
            edit = {"session_id": session, "cwd": str(root), "tool_name": "apply_patch",
                    "tool_input": {"command": "*** Begin Patch\n*** Update File: src/Jigsaw/Board.cs\n*** End Patch"}}
        assert run(agent, "post-tool", edit, root) == {}
        stop = run(agent, "stop", {"session_id": session, "stop_hook_active": False}, root)
        assert stop["decision"] == "block" and "gameplay.Jigsaw" in stop["reason"]
        assert "hookSpecificOutput" not in stop
        assert run(agent, "stop", {"session_id": session, "stop_hook_active": True}, root) == {}


def test_post_tool_record_counts_as_written(root):
    run("claude", "pre-tool", {"session_id": "s6", "tool_name": "mcp__pmem__search_memory",
                               "tool_input": {"module": "gameplay.Jigsaw"}}, root)
    run("claude", "post-tool", claude_edit(root, "src/Jigsaw/Board.cs", "s6"), root)
    response = json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E5", "module": "gameplay.Jigsaw"})
    run("claude", "post-tool", {"session_id": "s6", "tool_name": "mcp__pmem__record_memory",
                                "tool_input": {"module": "gameplay.Jigsaw"},
                                "tool_response": [{"type": "text", "text": response}]}, root)
    assert run("claude", "stop", {"session_id": "s6"}, root) == {}


def test_claude_gets_memory_digest_on_prompt_and_on_read(root):
    prompt = run("claude", "prompt", {"session_id": "s8", "prompt": "Jigsaw 的奖励怎么发"}, root)
    output = prompt["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit" and "旧结论" in output["additionalContext"]
    read = {"session_id": "s9", "tool_name": "Read", "tool_input": {"file_path": str(root / "src/Jigsaw/Board.cs")}}
    output = run("claude", "post-tool", read, root)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUse" and "gameplay.Jigsaw" in output["additionalContext"]


def test_codex_prompt_gets_memory_digest(root):
    output = run("codex", "prompt", {"session_id": "s10", "prompt": "Jigsaw 的奖励怎么发"}, root)["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit" and "旧结论" in output["additionalContext"]


def test_claude_powershell_tool_is_checked_like_bash(root):
    ps = {"session_id": "s11", "cwd": str(root), "tool_name": "PowerShell",
          "tool_input": {"command": "Set-Content src/Jigsaw/Board.cs 'x'"}}
    assert run("claude", "pre-tool", ps, root)["hookSpecificOutput"]["permissionDecision"] == "deny"
    ps["tool_input"]["command"] = "pmem search --module gameplay.Jigsaw 奖励"
    run("claude", "pre-tool", ps, root)
    run("claude", "post-tool", {**ps, "tool_response": {"stdout": "gameplay.Jigsaw：1 条", "stderr": ""}}, root)
    ps["tool_input"]["command"] = "Set-Content src/Jigsaw/Board.cs 'x'"
    assert run("claude", "pre-tool", ps, root) == {}


def test_hook_cli_with_agent_flag_finds_project_from_payload_cwd(root, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = json.dumps(claude_edit(root, "src/Jigsaw/Board.cs", "s7"), ensure_ascii=False).encode("utf-8")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    main(["hook", "pre-tool", "--agent", "claude"])
    out = capsys.readouterr().out
    assert out.isascii()
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_hook_cli_outside_project_prints_empty_object_for_other_agents(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    main(["hook", "pre-tool", "--agent", "codex"])
    assert json.loads(capsys.readouterr().out) == {}
