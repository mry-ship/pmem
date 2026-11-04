import json

import pytest

from pmem.catalog.yamlfile import ModulesFile
from pmem.generate.integrations import BLOCK_BEGIN, BLOCK_END, merge_group_hooks, merge_hooks, upsert_block

BLOCK = f"{BLOCK_BEGIN}\npmem 段落\n{BLOCK_END}\n"


def test_upsert_block_without_end_marker_keeps_user_text(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(f"{BLOCK_BEGIN}\n旧段落\n\n用户自己的说明\n", encoding="utf-8")
    upsert_block(path, BLOCK)
    upsert_block(path, BLOCK)
    text = path.read_text(encoding="utf-8")
    assert "用户自己的说明" in text and text.count(BLOCK_BEGIN) == 1


def test_group_hooks_drop_pmem_handlers_of_events_no_longer_used(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"hooks": {
        "Old": [{"hooks": [{"type": "command", "command": "pmem hook old"}]}],
        "Mixed": [{"hooks": [{"type": "command", "command": "pmem hook x"}, {"type": "command", "command": "lint"}]}],
    }}), encoding="utf-8")
    merge_group_hooks(path, {"Stop": [{"hooks": [{"type": "command", "command": "pmem hook stop"}]}]})
    hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    assert "Old" not in hooks
    assert hooks["Mixed"] == [{"hooks": [{"type": "command", "command": "lint"}]}]
    assert hooks["Stop"][0]["hooks"][0]["command"] == "pmem hook stop"


@pytest.mark.parametrize("hooks", [[], {"stop": {"command": "x"}}])
def test_malformed_hooks_json_reports_instead_of_crashing(tmp_path, hooks):
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
    with pytest.raises(SystemExit, match="hooks"):
        merge_hooks(path)


def test_non_dict_hook_entries_are_kept(tmp_path):
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({"hooks": {"stop": ["legacy"]}}), encoding="utf-8")
    merge_hooks(path)
    assert "legacy" in json.loads(path.read_text(encoding="utf-8"))["hooks"]["stop"]


def test_merge_hooks_quiet_drops_post_tool_use(tmp_path):
    from pmem.generate.templates import CURSOR_HOOKS_FULL, CURSOR_HOOKS_QUIET

    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({"version": 1, "hooks": {
        "sessionStart": [{"command": "pmemw hook session"}],
        "stop": [{"command": "my-own-hook"}, {"command": "pmemw hook stop"}],
        "preToolUse": [{"command": "security-scan"}],
        "postToolUse": [{"command": "pmemw hook post-tool", "matcher": "Read"}],
    }}), encoding="utf-8")
    merge_hooks(path, CURSOR_HOOKS_FULL)
    full = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    assert "postToolUse" in full and "afterFileEdit" in full
    assert full["stop"][0] == {"command": "my-own-hook"}
    assert full["stop"][1]["command"] == "pmemw hook stop"
    assert full["preToolUse"][0]["command"] == "security-scan"

    merge_hooks(path, CURSOR_HOOKS_QUIET)
    quiet = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    assert quiet["postToolUse"][0]["matcher"] == "Shell"
    assert "Read" not in quiet["postToolUse"][0]["matcher"]
    assert "afterFileEdit" not in quiet
    assert "preCompact" not in quiet
    assert quiet["preToolUse"][0]["command"] == "security-scan"
    assert any(h.get("command") == "pmemw hook pre-tool" for h in quiet["preToolUse"])


def test_cursor_hooks_auto_quiet_on_windows(monkeypatch):
    import sys

    from pmem.generate.templates import cursor_hooks

    monkeypatch.setattr(sys, "platform", "win32")
    quiet = cursor_hooks("auto")
    assert quiet["postToolUse"]["matcher"] == "Shell"
    assert "afterFileEdit" not in quiet
    monkeypatch.setattr(sys, "platform", "linux")
    full = cursor_hooks("auto")
    assert "Read" in full["postToolUse"]["matcher"]
    assert "afterFileEdit" in full
    assert cursor_hooks("full")["postToolUse"]["matcher"].startswith("Read")
    assert cursor_hooks("quiet")["postToolUse"]["matcher"] == "Shell"


def test_comment_only_modules_yaml_without_newline_keeps_body(tmp_path):
    path = tmp_path / "modules.yaml"
    path.write_text("# 只有注释", encoding="utf-8")
    ModulesFile.read(path).write({"modules": {"a.B": {}}})
    assert ModulesFile.read(path).data == {"modules": {"a.B": {}}}
