"""harness 实验：search_memory 附 context、无记忆轻提示、Stop 漏改/验证检查；off 时与旧行为一致。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pmem import context
from pmem.core.config import Config
from pmem.hooks.gate import handle
from pmem.hooks.state import SessionState
from pmem.metrics.events import read_events
from pmem.metrics.report import _harness, render
from pmem.service import MemoryService

from tests.hooks.test_gate import CONFIG, MODULES, ENTRY, search_done, write_payload


@pytest.fixture
def harness_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))

    def build(mode="hint", verify=None, with_memory=True) -> Path:
        root = tmp_path / f"proj-{mode}-{with_memory}"
        (root / ".memory").mkdir(parents=True, exist_ok=True)
        harness = f"harness: {{ mode: {mode}"
        if verify:
            cmds = ", ".join(f'"{c}"' for c in verify)
            harness += f", verify_commands: [{cmds}]"
        harness += " }\n"
        (root / ".memory" / "config.yaml").write_text(
            CONFIG.format(mode="block") + harness, encoding="utf-8")
        (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
        (root / "src" / "Jigsaw").mkdir(parents=True, exist_ok=True)
        (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board {}\n", encoding="utf-8")
        (root / "src" / "Jigsaw" / "Score.cs").write_text("class Score {}\n", encoding="utf-8")
        (root / "src" / "Shop").mkdir(parents=True, exist_ok=True)
        (root / "src" / "Shop" / "Shop.cs").write_text("class Shop {}\n", encoding="utf-8")
        if with_memory:
            folder = root / ".memory" / "entries" / "gameplay.Jigsaw"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(
                ENTRY.format(id="01JA7K3M2X9F4Q8W6ZB1C2D3E4", module="gameplay.Jigsaw"), encoding="utf-8")
        context.save(Config.load(root).cache_dir, {
            "built": 1, "window": 180, "vcs": "none", "commits": 3,
            "files": {
                "src/Jigsaw/Board.cs": {
                    "n": 3,
                    "co": [["src/Jigsaw/Score.cs", 3]],
                    "fix": [["2026-11-01", "fix board null"]],
                },
            },
        })
        return root

    return build


def stop_payload(conv="c1") -> dict:
    return {"conversation_id": conv, "hook_event_name": "stop", "status": "completed", "loop_count": 0}


def edit(root: Path, rel: str, conv="c1") -> dict:
    """Cursor 用 afterFileEdit（edited）记改动；Claude/Codex 走 post-tool 的 file_paths。"""
    return handle("edited", {"conversation_id": conv, "file_path": str(root / rel)}, root)


def test_off_mode_matches_old_gate_behavior(harness_project):
    root = harness_project("off")
    denied = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert denied["permission"] == "deny"
    assert "常一起改" not in denied["user_message"]
    assert 'path="src/Jigsaw/Board.cs"' in denied["user_message"]
    assert edit(root, "src/Jigsaw/Board.cs") == {}


def test_search_attaches_context_with_path(harness_project):
    root = harness_project("hint")
    service = MemoryService(root, source="mcp")
    try:
        result = service.search(module="gameplay.Jigsaw", path="src/Jigsaw/Board.cs",
                                source_conversation="c1")
    finally:
        service.close()
    assert "context" in result
    assert "src/Jigsaw/Score.cs" in result["context"]
    assert "fix board null" in result["context"]


def test_gate_message_does_not_embed_harness_hint(harness_project):
    root = harness_project("hint")
    denied = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert denied["permission"] == "deny"
    assert "常一起改" not in denied["user_message"]
    assert 'search_memory(module="gameplay.Jigsaw", path="src/Jigsaw/Board.cs")' in denied["user_message"]


def test_empty_module_allows_and_tips_after_edit(harness_project):
    root = harness_project("hint", with_memory=False)
    assert handle("pre-tool", write_payload(root, "src/Shop/Shop.cs"), root)["permission"] == "allow"
    tip = edit(root, "src/Shop/Shop.cs")
    assert "additional_context" in tip
    assert 'search_memory(module="economy.Shop", path="src/Shop/Shop.cs")' in tip["additional_context"]
    assert edit(root, "src/Shop/Shop.cs") == {}


def test_check_stop_nudges_missing_partner_and_verify(harness_project):
    root = harness_project("check", verify=["pytest"])
    search_done(root)
    edit(root, "src/Jigsaw/Board.cs")
    stop = handle("stop", stop_payload(), root)
    text = stop["followup_message"]
    assert "src/Jigsaw/Score.cs" in text
    assert "验证命令" in text and "pytest" in text
    events = list(read_events(Config.load(root).cache_dir))
    assert any(e["type"] == "harness_nudge" and "src/Jigsaw/Score.cs" in (e.get("partners") or []) for e in events)
    assert any(e["type"] == "harness_verify" and e.get("ran") is False for e in events)


def test_check_stop_skips_verify_when_command_ran(harness_project):
    root = harness_project("check", verify=["pytest"])
    search_done(root)
    edit(root, "src/Jigsaw/Board.cs")
    handle("pre-tool", {
        "conversation_id": "c1", "tool_name": "Shell",
        "tool_input": {"command": "pytest tests/hooks", "cwd": ""},
    }, root)
    # 伙伴文件也改了，只应看到验证已跑、不再催验证；漏改也不再提
    edit(root, "src/Jigsaw/Score.cs")
    stop = handle("stop", stop_payload(), root)
    # 还有功能记录提醒
    assert "验证命令" not in (stop.get("followup_message") or "")
    assert any(e["type"] == "harness_verify" and e.get("ran") for e in read_events(Config.load(root).cache_dir))


def test_spec_must_keep_appears_in_search_context(harness_project):
    root = harness_project("hint")
    status = root / ".memory" / "specs" / "gameplay.Jigsaw" / "模块现状.md"
    status.parent.mkdir(parents=True)
    status.write_text("必须保持：回放分数不变。\n", encoding="utf-8")
    service = MemoryService(root, source="mcp")
    try:
        result = service.search(module="gameplay.Jigsaw", path="src/Jigsaw/Board.cs",
                                source_conversation="c2")
    finally:
        service.close()
    assert "回放分数不变" in result["context"]


def test_harness_report_metrics():
    events = [
        {"ts": 100, "type": "harness_nudge", "conv": "c1", "partners": ["src/b.py"], "files": ["src/a.py"]},
        {"ts": 110, "type": "edit", "conv": "c1", "file": "src/b.py"},
        {"ts": 120, "type": "harness_verify", "ran": True, "commands": ["pytest"]},
        {"ts": 130, "type": "harness_verify", "ran": False, "commands": ["pytest"]},
        {"ts": 140, "type": "edit", "file": "src/a.py"},
        {"ts": 140 + 86400, "type": "edit", "file": "src/a.py"},
        {"ts": 200, "type": "context_nudge", "conv": "c2", "file": "src/c.py", "reason": "empty"},
        {"ts": 210, "type": "context", "conv": "c2", "file": "src/c.py", "via": "search"},
    ]
    stats = _harness(events)
    assert stats["co_adopted"] == 1 and stats["co_partners"] == 1
    assert stats["verify_ran"] == 1 and stats["verify_checks"] == 2
    assert stats["reworked_files"] == 1 and stats["edited_files"] == 2
    assert stats["empty_followed"] == 1
    text = render({
        "days": 30,
        "search": {"total": 0, "hits": 0, "avoided": 0, "reused": 0, "reused_authors": 0},
        "citations": {"returned": 0, "cited": 0},
        "records": {"total": 0, "by_kind": {}},
        "habits": {"gates": 0, "gate_converted": 0, "nudges": 0, "nudge_converted": 0},
        "usage": {"returned_memories": 0, "top": [], "review": [], "idle": 0, "idle_modules": []},
        "compare": {"hit": {"n": 0, "input_tokens": None, "output_tokens": None, "turns": None, "edits": None, "minutes": None},
                    "miss": {"n": 0, "input_tokens": None, "output_tokens": None, "turns": None, "edits": None, "minutes": None},
                    "enough": False},
        "assets": {"memories": 0, "new": 0, "modules_with_memory": 0, "modules_registered": 0,
                   "single_author": [], "hot": [], "uncommitted": None},
        "harness": stats,
    })
    assert "漏改提示采纳" in text and "验证回合" in text and "返工率" in text
