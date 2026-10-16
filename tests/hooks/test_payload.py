import json
from pathlib import Path

import pytest

from pmem.hooks.payload import asks_to_skip, fuzzy_contains, last_user_text, parse_payload, tool_input, workspace_root

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


@pytest.mark.parametrize("text, expected", [
    ("跳过记忆", True),
    ("这次跳过记忆，直接改", True),
    ("跳过记忆吧", True),
    ("please skip-memory", True),
    ("如何避免单次问询 跳过记忆审查？", False),
    ("不要跳过记忆", False),
    ("跳过记忆的逻辑有问题", False),
    ("给拼图加个关卡", False),
])
def test_asks_to_skip_only_for_requests(text, expected):
    marker = "skip-memory" if text.isascii() else "跳过记忆"
    assert asks_to_skip(text, marker) is expected


def test_asks_to_skip_on_cursor_garbled_prompt():
    def garble(text: str) -> str:
        return text.encode("utf-8").decode("gbk", errors="replace")

    assert not asks_to_skip(garble("补充：如何避免单次问询 跳过记忆审查？"), "跳过记忆")
    assert asks_to_skip(garble("这次跳过记忆"), "跳过记忆")


def _jsonl(path: Path, records: list[dict]) -> str:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    return str(path)


def test_last_user_text_reads_cursor_transcript(tmp_path):
    text = "<timestamp>t</timestamp>\n<attached_files>附件</attached_files>\n<user_query>\n拼图奖励为什么重复？\n</user_query>"
    path = _jsonl(tmp_path / "c.jsonl", [
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>旧问题</user_query>"}]}},
        {"role": "user", "message": {"content": [{"type": "text", "text": text}]}},
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "回答"}]}},
        {"type": "turn_ended", "status": "completed"},
    ])
    assert last_user_text(path) == "拼图奖励为什么重复？"


def test_last_user_text_skips_claude_tool_results(tmp_path):
    path = _jsonl(tmp_path / "c.jsonl", [
        {"type": "user", "message": {"role": "user", "content": "看下 Jigsaw"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "好"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}},
    ])
    assert last_user_text(path) == "看下 Jigsaw"


def test_last_user_text_handles_missing_file_and_cursor_path(tmp_path):
    assert last_user_text(None) is None
    assert last_user_text(str(tmp_path / "missing.jsonl")) is None
    path = _jsonl(tmp_path / "c.jsonl", [{"role": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}])
    if path[1] == ":":
        assert last_user_text("/" + path.replace("\\", "/")) == "hi"


# ---- Windows 代码页 936 误解码：私有区字符要能还原 ----

def _win936_decode(data: bytes) -> str:
    """模拟 Cursor 在中文 Windows 上把 UTF-8 字节按代码页 936 解码（含用户自定义区到私有区的映射）。"""
    from pmem.hooks.payload import _pua_bytes

    pua = {_pua_bytes(chr(c)): chr(c) for c in range(0xE000, 0xE766)}
    out, i = [], 0
    while i < len(data):
        if data[i] < 0x80:
            out.append(chr(data[i]))
            i += 1
            continue
        pair = data[i:i + 2]
        try:
            out.append(pair.decode("gbk"))
        except UnicodeDecodeError:
            out.append(pua.get(pair, "\ufffd"))
        i += 2
    return "".join(out)


def test_pua_mapping_matches_windows_samples():
    from pmem.hooks.payload import _pua_bytes

    assert _pua_bytes("\ue6c2") == b"\xa6\x5c"
    assert _pua_bytes("\ue21a") == b"\xaf\xe5"
    assert _pua_bytes("a") is None


def test_backslash_swallowed_by_garbling_is_restored():
    from pmem.hooks.gate import cli_args

    command = 'pmem record --module a.B --alias 通配符\npmem record --module c.D --alias x'
    raw = json.dumps({"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"command": command}},
                     ensure_ascii=False).encode("utf-8")
    garbled = _win936_decode(raw)
    assert "\ue6c2" in garbled
    data = parse_payload(b"\xef\xbb\xbf" + garbled.encode("utf-8"))
    assert tool_input(data)["command"] == command
    assert cli_args(tool_input(data)["command"], "record") == [{"module": "a.B"}, {"module": "c.D"}]


def test_merged_commands_keep_the_first_module():
    from pmem.hooks.gate import cli_args

    assert cli_args("pmem record --module a.B --alias 符npmem record --module c.D", "record") == [{"module": "a.B"}]
