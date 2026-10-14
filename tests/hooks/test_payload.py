import json
from pathlib import Path

import pytest

from pmem.hooks.payload import fuzzy_contains, parse_payload, tool_input, workspace_root

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "hook_payloads"


def load(name: str) -> dict:
    return parse_payload((FIXTURES / f"{name}.json").read_bytes())


@pytest.mark.parametrize("name", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_every_recorded_payload_yields_conversation_and_event(name):
    data = load(name)
    assert data["conversation_id"] == "4d3f8f86-94f3-49be-8945-3425256f37e8"
    assert data["hook_event_name"] == name.split("_")[0]


def test_write_payload_with_broken_json_still_gives_path():
    data = load("preToolUse_Write")
    assert data["tool_name"] == "Write"
    assert tool_input(data)["file_path"].startswith("C:\\work\\demo\\")


def test_mangled_after_file_edit_gives_path():
    data = load("afterFileEdit_mangled")
    assert data["file_path"].endswith("playground.txt")


def test_shell_payload_gives_command():
    data = load("preToolUse_Shell")
    assert data["tool_name"] == "Shell"
    assert "playground2.txt" in tool_input(data)["command"]


def test_plain_utf8_without_bom_parses():
    data = parse_payload('{"conversation_id":"c1","prompt":"跳过记忆"}'.encode())
    assert data["prompt"] == "跳过记忆"


@pytest.mark.parametrize("prompt", ["请跳过记忆再改", "跳过记忆", "好的，这次跳过记忆。", "a跳过记忆"])
def test_marker_is_found_in_gbk_mangled_prompt(prompt):
    original = json.dumps({"conversation_id": "c1", "prompt": prompt}, ensure_ascii=False)
    mangled = "\ufeff" + original.encode("utf-8").decode("gbk", errors="replace")
    data = parse_payload(mangled.encode("utf-8"))
    assert data["conversation_id"] == "c1"
    assert fuzzy_contains(data["prompt"], "跳过记忆")
    assert not fuzzy_contains(data["prompt"], "不相关")


def test_tool_input_accepts_json_string():
    assert tool_input({"tool_input": '{"module":"a.B"}'}) == {"module": "a.B"}


def test_workspace_root_converts_cursor_style_path():
    assert workspace_root({"workspace_roots": ["/c:/work/demo"]}) == "c:/work/demo"
    assert workspace_root({"workspace_roots": ["/home/me/demo"]}) == "/home/me/demo"
    assert workspace_root({}) is None


def test_garbage_input_gives_empty_dict():
    assert parse_payload(b"\xff\xfe not json") == {}
