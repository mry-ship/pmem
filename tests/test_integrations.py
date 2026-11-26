import json

import pytest

from pmem.catalog.yamlfile import ModulesFile
from pmem.generate.integrations import BLOCK_BEGIN, BLOCK_END, merge_group_hooks, merge_hooks, upsert_block
from pmem.generate.templates import (
    MINIMAL_SKILL,
    QUALITY_BEGIN,
    QUALITY_BODY,
    QUALITY_END,
    QUALITY_RULE,
    QUALITY_RULE_BLOCK,
    REVIEW_SKILL,
    RULE_BODY,
)

BLOCK = f"{BLOCK_BEGIN}\npmem 段落\n{BLOCK_END}\n"


def test_upsert_block_without_end_marker_keeps_user_text(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(f"{BLOCK_BEGIN}\n旧段落\n\n用户自己的说明\n", encoding="utf-8")
    upsert_block(path, BLOCK)
    upsert_block(path, BLOCK)
    text = path.read_text(encoding="utf-8")
    assert "用户自己的说明" in text and text.count(BLOCK_BEGIN) == 1
    assert text.index("用户自己的说明") < text.index(BLOCK_BEGIN)


def test_quality_markers_do_not_overwrite_memory_or_user_text(tmp_path):
    path = tmp_path / "CLAUDE.md"
    path.write_text("# 项目说明\n团队约定 A\n", encoding="utf-8")
    upsert_block(path, BLOCK)
    upsert_block(path, QUALITY_RULE_BLOCK, QUALITY_BEGIN, QUALITY_END)
    upsert_block(path, BLOCK)
    upsert_block(path, QUALITY_RULE_BLOCK, QUALITY_BEGIN, QUALITY_END)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# 项目说明\n团队约定 A\n")
    assert text.count(BLOCK_BEGIN) == 1 and text.count(BLOCK_END) == 1
    assert text.count(QUALITY_BEGIN) == 1 and text.count(QUALITY_END) == 1
    assert "pmem 段落" in text and "工程质量" in text
    assert "pmem-minimal" not in RULE_BODY


def test_quality_block_missing_end_keeps_following_text(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(
        "团队约定 A\n\n"
        f"{BLOCK_BEGIN}\n记忆\n{BLOCK_END}\n\n"
        f"{QUALITY_BEGIN}\n旧质量\n\n用户自己的说明\n",
        encoding="utf-8",
    )
    upsert_block(path, QUALITY_RULE_BLOCK, QUALITY_BEGIN, QUALITY_END)
    text = path.read_text(encoding="utf-8")
    assert "团队约定 A" in text and "记忆" in text and "用户自己的说明" in text
    assert text.count(BLOCK_BEGIN) == 1 and text.count(QUALITY_BEGIN) == 1
    assert text.index(BLOCK_BEGIN) < text.index("旧质量") < text.index("用户自己的说明") < text.index(QUALITY_BEGIN)
    assert "旧质量" not in text.split(QUALITY_BEGIN, 1)[1]
    upsert_block(path, QUALITY_RULE_BLOCK, QUALITY_BEGIN, QUALITY_END)
    text = path.read_text(encoding="utf-8")
    assert text.count(QUALITY_BEGIN) == 1 and text.count(BLOCK_BEGIN) == 1
    assert "用户自己的说明" in text and "记忆" in text


def test_quality_templates_format_and_keep_frozen_triggers():
    for body in (QUALITY_RULE, MINIMAL_SKILL, REVIEW_SKILL):
        body.format(generated="x")
    assert "只在用户点名时加载" in QUALITY_BODY and "不因改动大小自动触发" in QUALITY_BODY
    assert "仍按 pmem 记忆规则" in QUALITY_BODY
    assert "用户明确要求" in REVIEW_SKILL and "不因新增文件" in REVIEW_SKILL
    assert "没有点名审查时，不强制完整审查" in REVIEW_SKILL
    for state in ("未触及", "符合", "违反", "待核实"):
        assert state in REVIEW_SKILL
    assert "待对照代码核对" in REVIEW_SKILL and "不能标成违反" in REVIEW_SKILL
    assert "排除项" in REVIEW_SKILL and "决定" in REVIEW_SKILL and "约束核对逐条一行" in REVIEW_SKILL
    assert "先处理需核实" not in REVIEW_SKILL and "先处理需核实" not in RULE_BODY and "先处理需核实" not in QUALITY_BODY
    assert "用户明确要求审查时，即使只改了一个文件，也要执行" in REVIEW_SKILL
    assert "没有新增文件、依赖、模块、抽象，也没有跨模块改动时，不做这份完整审查" not in REVIEW_SKILL
    assert "不运行 pmem spec complete" in MINIMAL_SKILL
    assert "pmem-minimal" not in RULE_BODY and "跳过质量" not in RULE_BODY
    # 工程原则放独立质量段，不进记忆规则正文（见记忆「MinimalChange」排除项）
    assert "最小改动" not in RULE_BODY
    assert "只做当前任务所需的最小改动，复用现有写法，改完核对调用方与边界" in QUALITY_BODY
    assert "只清理本次新增的冗余" in QUALITY_BODY and "不顺手重构既有代码" in QUALITY_BODY
    assert "3 个及以上文件" in QUALITY_BODY and "不打印审查表格" in QUALITY_BODY
    assert "spec.read_before_edit 为 true" in MINIMAL_SKILL


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


def test_merge_hooks_quiet_keeps_gate_drops_read_digest(tmp_path):
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
    assert "sessionStart" in quiet and "beforeSubmitPrompt" in quiet and "stop" in quiet
    assert "afterFileEdit" not in quiet and "preCompact" not in quiet
    assert "afterMCPExecution" in quiet
    assert quiet["postToolUse"][-1]["matcher"] == "Shell"
    assert "Write" in quiet["preToolUse"][-1]["matcher"] and "Shell" in quiet["preToolUse"][-1]["matcher"]
    assert quiet["preToolUse"][0]["command"] == "security-scan"
    assert any(h.get("command") == "pmemw hook pre-tool" for h in quiet["preToolUse"])
    assert quiet["stop"][0] == {"command": "my-own-hook"}
    assert quiet["stop"][1]["command"] == "pmemw hook stop"


def _hook_commands(tree) -> list[str]:
    """Flatten Cursor / Claude / Codex hook trees into command strings."""
    if not isinstance(tree, dict):
        return []
    out = []
    for entries in tree.values():
        if isinstance(entries, dict) and "command" in entries:
            out.append(str(entries["command"]))
            continue
        if not isinstance(entries, list):
            continue
        for item in entries:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("command"), str):
                out.append(item["command"])
            for handler in item.get("hooks") or []:
                if isinstance(handler, dict) and isinstance(handler.get("command"), str):
                    out.append(handler["command"])
    return out


def test_template_hooks_never_use_console_launchers():
    """Windows 上 Hook 必须是 GUI 入口 pmemw，禁止 pmem/.cmd/||/控制台 python。"""
    from pmem.generate.templates import (
        CLAUDE_HOOKS_FULL,
        CLAUDE_HOOKS_QUIET,
        CODEX_HOOKS_FULL,
        CODEX_HOOKS_QUIET,
        CURSOR_HOOKS_FULL,
        CURSOR_HOOKS_QUIET,
        HOOK_BIN,
        MCP_BIN,
    )

    assert HOOK_BIN == "pmemw" and MCP_BIN == "pmem"
    for name, tree in (
        ("cursor_full", CURSOR_HOOKS_FULL),
        ("cursor_quiet", CURSOR_HOOKS_QUIET),
        ("claude_full", CLAUDE_HOOKS_FULL),
        ("claude_quiet", CLAUDE_HOOKS_QUIET),
        ("codex_full", CODEX_HOOKS_FULL),
        ("codex_quiet", CODEX_HOOKS_QUIET),
    ):
        cmds = _hook_commands(tree)
        assert cmds, name
        for cmd in cmds:
            assert cmd.startswith("pmemw hook"), f"{name}: {cmd}"
            assert "||" not in cmd and ".cmd" not in cmd and "pmem-hook" not in cmd
            assert not cmd.startswith(("pmem ", "python", "py ", "cmd"))


def test_cursor_hooks_auto_is_full_everywhere(monkeypatch):
    import sys

    from pmem.generate.templates import claude_hooks, codex_hooks, cursor_hooks

    monkeypatch.setattr(sys, "platform", "win32")
    auto = cursor_hooks("auto")
    assert "afterFileEdit" in auto and "preCompact" in auto
    assert "Read" in auto["postToolUse"]["matcher"] and "Shell" in auto["postToolUse"]["matcher"]
    assert "Write" in auto["preToolUse"]["matcher"] and "sessionStart" in auto and "stop" in auto
    assert claude_hooks("auto", paired_with_cursor=True) == {}
    assert claude_hooks("full", paired_with_cursor=True) == {}
    assert "Read" in claude_hooks("auto", paired_with_cursor=False)["PostToolUse"][0]["matcher"]
    assert cursor_hooks("off") == {}
    codex_auto = codex_hooks("auto")
    assert "PreCompact" in codex_auto and "UserPromptSubmit" in codex_auto and "Stop" in codex_auto
    assert "Bash" in codex_auto["PreToolUse"][0]["matcher"]
    quiet = cursor_hooks("quiet")
    assert "afterFileEdit" not in quiet and quiet["postToolUse"]["matcher"] == "Shell"
    assert "Write" in quiet["preToolUse"]["matcher"]
    monkeypatch.setattr(sys, "platform", "linux")
    full = cursor_hooks("auto")
    assert "Read" in full["postToolUse"]["matcher"] and "afterFileEdit" in full
    assert "Write" in cursor_hooks("full")["preToolUse"]["matcher"]
    assert "Read" in claude_hooks("full")["PostToolUse"][0]["matcher"]
    assert "UserPromptSubmit" in codex_hooks("auto") and "Stop" in codex_hooks("full")


def test_comment_only_modules_yaml_without_newline_keeps_body(tmp_path):
    path = tmp_path / "modules.yaml"
    path.write_text("# 只有注释", encoding="utf-8")
    ModulesFile.read(path).write({"modules": {"a.B": {}}})
    assert ModulesFile.read(path).data == {"modules": {"a.B": {}}}
