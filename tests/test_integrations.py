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


def test_comment_only_modules_yaml_without_newline_keeps_body(tmp_path):
    path = tmp_path / "modules.yaml"
    path.write_text("# 只有注释", encoding="utf-8")
    ModulesFile.read(path).write({"modules": {"a.B": {}}})
    assert ModulesFile.read(path).data == {"modules": {"a.B": {}}}
