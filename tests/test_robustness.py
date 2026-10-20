"""坏输入、外部命令失败时给可读的错误：文件头字段写错、版本库不可用、配置取值不对、命令参数越界。"""
import warnings
from pathlib import Path
from unittest import mock

import pytest

from pmem.cli.main import main
from pmem.core.config import Config, ConfigError
from pmem.core.entry import Entry
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.hooks.state import SessionState
from pmem.index.anchors import _python_tree
from pmem.service import MemoryService
from pmem.vcs.base import run_tool
from pmem.vcs.svn import SvnVCS

HEAD = "---\nid: 01JA7K3M2X9F4Q8W6ZB1C2D3E4\nmodule: gameplay.Jigsaw\nentity: Reward\nkind: risk\nnote_date: '2026-10-01'\n"


def test_single_value_list_fields_are_read_as_one_item():
    entry = Entry.from_markdown(HEAD + "supersedes: 01JA7K3M2X9F4Q8W6ZB1C2D3E5\naliases: 闪退\n---\n正文")
    assert entry.supersedes == ["01JA7K3M2X9F4Q8W6ZB1C2D3E5"] and entry.aliases == ["闪退"]
    with pytest.raises(ValueError, match="supersedes"):
        Entry.from_markdown(HEAD + "supersedes: {a: 1}\n---\n正文")


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory" / "entries" / "gameplay.Jigsaw").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n", encoding="utf-8")
    return root


def test_confirm_reports_bad_files_and_keeps_going(project):
    folder = project / ".memory" / "entries" / "gameplay.Jigsaw"
    (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(HEAD + "supersedes: {a: 1}\n---\n正文正文正文", encoding="utf-8")
    good = HEAD.replace("E4", "E5") + "---\n另一条正文"
    (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3E5.md").write_text(good, encoding="utf-8")
    svc = MemoryService(project)
    try:
        result = svc.confirm(["01JA7K3M2X9F4Q8W6ZB1C2D3E4", "01JA7K3M2X9F4Q8W6ZB1C2D3E5"])
    finally:
        svc.close()
    assert result["confirmed"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E5"]
    assert [i["id"] for i in result["invalid"]] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]


def test_missing_vcs_binary_is_a_failed_command_not_an_exception(tmp_path):
    proc = run_tool(["pmem-no-such-tool-xyz"], tmp_path)
    assert proc.returncode == 127


def test_svn_status_error_means_unknown_commit_state(tmp_path):
    svn = SvnVCS(tmp_path)
    with mock.patch.object(SvnVCS, "_item_status", return_value=None):
        assert svn.is_committed(tmp_path / "a.md") is None
    with mock.patch.object(SvnVCS, "_item_status", return_value="added"):
        assert svn.is_committed(tmp_path / "a.md") is False


def test_entity_with_any_line_break_is_rejected(project):
    svc = MemoryService(project)
    try:
        for entity in ("Foo\rBar", "Foo\u2028Bar", "Foo\x07"):
            result = svc.record("gameplay.Jigsaw", entity, "risk", "领取按钮没有防连点导致重复发奖。")
            assert result["code"] == "entity_invalid", entity
    finally:
        svc.close()


def test_parsing_user_code_does_not_print_syntax_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _python_tree('x = "\\d+"\n') is not None


@pytest.mark.parametrize(("raw", "message"), [
    ({"write": {"content_min": "abc"}}, "write.content_min"),
    ({"write": {"content_min": 50, "content_max": 10}}, "content_max"),
    ({"search": {"limit": 0}}, "search.limit"),
    ({"gate": "on"}, "gate"),
    ({"gate": {"watch": {"a": 1}}}, "gate.watch"),
])
def test_bad_config_values_are_rejected_up_front(tmp_path, raw, message):
    from pmem.core.config import DEFAULTS, _merge

    with pytest.raises(ConfigError, match=message):
        Config(tmp_path, _merge(DEFAULTS, raw))


def test_single_string_list_setting_becomes_a_list(tmp_path):
    from pmem.core.config import DEFAULTS, _merge

    assert Config(tmp_path, _merge(DEFAULTS, {"gate": {"watch": "src/**"}})).get("gate.watch") == ["src/**"]


def test_missing_categories_are_inferred_instead_of_game_preset():
    assert ModuleRegistry({}).categories == ["feature", "infra"]
    registry = ModuleRegistry({"modules": {"feature.Login": {"paths": ["src/**"]}}})
    assert registry.categories == ["feature"]


def test_broken_modules_yaml_gives_one_line_and_exit_2(project, capsys):
    (project / ".memory" / "modules.yaml").write_text("modules: [\n", encoding="utf-8")
    for command in (["sync"], ["migrate", "tidy"], ["compact"], ["reindex"], ["search", "--module", "x"]):
        assert main([*command, "--root", str(project)]) == 2, command
        assert "格式错误" in capsys.readouterr().err


def test_numeric_flags_must_be_positive(project):
    with pytest.raises(SystemExit) as exc:
        main(["search", "--module", "gameplay.Jigsaw", "--limit", "-3", "--root", str(project)])
    assert exc.value.code == 2


def test_wiki_out_pointing_at_a_file_is_rejected(project, capsys):
    (project / "notes.md").write_text("x", encoding="utf-8")
    assert main(["wiki", "--out", "notes.md", "--root", str(project)]) == 2
    assert "应是目录" in capsys.readouterr().err


def test_bench_cases_file_with_list_top_level_is_rejected(project, capsys):
    (project / "cases.yaml").write_text("- id: a\n", encoding="utf-8")
    assert main(["bench", "cases.yaml", "--dry-run", "--root", str(project)]) == 2
    assert "用例文件有误" in capsys.readouterr().err


def test_scan_of_a_small_project_still_lists_directories(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    main(["scan", "--root", str(tmp_path)])
    assert "[src]" in capsys.readouterr().out


def test_session_lock_is_reentrant(tmp_path):
    state = SessionState(tmp_path, "c1")
    with state.locked():
        state.data["skip"] = True
        with state.locked():
            assert state.data["skip"] is True
        state.save()
    with state.locked():
        assert state.data["skip"] is True


def test_registry_error_for_broken_yaml_in_catalog_reader(project):
    from pmem.catalog.yamlfile import ModulesFile

    (project / ".memory" / "modules.yaml").write_text("# 注释\nmodules: [\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="第 3 行"):
        ModulesFile.read(project / ".memory" / "modules.yaml")
