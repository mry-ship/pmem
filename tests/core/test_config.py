from pathlib import Path

import pytest

from pmem.core.config import Config, ConfigError, find_root


def write_config(root: Path, text: str) -> None:
    (root / ".memory").mkdir(parents=True, exist_ok=True)
    (root / ".memory" / "config.yaml").write_text(text, encoding="utf-8")


def test_defaults_fill_missing_keys(tmp_path):
    write_config(tmp_path, "project: { name: demo }\ngate: { mode: block }\n")
    cfg = Config.load(tmp_path)
    assert cfg.get("project.name") == "demo"
    assert cfg.get("gate.mode") == "block"
    assert cfg.get("gate.skip_markers") == ["跳过记忆", "skip-memory"]
    assert cfg.get("search.limit") == 5
    assert cfg.get("vcs") == "auto"


def test_empty_config_file_uses_defaults(tmp_path):
    write_config(tmp_path, "")
    assert Config.load(tmp_path).get("write.max_per_day_per_entity") == 5


def test_invalid_gate_mode_is_rejected(tmp_path):
    write_config(tmp_path, "gate: { mode: strict }\n")
    with pytest.raises(ConfigError, match="gate.mode"):
        Config.load(tmp_path)


@pytest.mark.parametrize("text, problem", [
    ("vcs: [unclosed\n", "无法解析"),
    ("- a\n- b\n", "顶层应是键值对"),
    ("write: { secret_patterns: ['(unclosed'] }\n", "不是有效的正则"),
    ("write: { secret_patterns: 'token' }\n", "正则表达式列表"),
])
def test_broken_config_raises_config_error(tmp_path, text, problem):
    write_config(tmp_path, text)
    with pytest.raises(ConfigError, match=problem):
        Config.load(tmp_path)


def test_find_root_walks_up(tmp_path):
    write_config(tmp_path, "")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_root(nested) == tmp_path.resolve()


def test_find_root_returns_none_outside_project(tmp_path):
    assert find_root(tmp_path) is None


def test_parsed_yaml_is_cached_until_the_file_changes(tmp_path, monkeypatch):
    write_config(tmp_path, "project: { name: demo }\n")
    assert Config.load(tmp_path).get("project.name") == "demo"
    import yaml

    monkeypatch.setattr(yaml, "safe_load", lambda text: pytest.fail("命中缓存时不应再解析 YAML"))
    assert Config.load(tmp_path).get("project.name") == "demo"
    monkeypatch.undo()
    write_config(tmp_path, "project: { name: renamed }\n")
    assert Config.load(tmp_path).get("project.name") == "renamed"


def test_paths_and_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    write_config(tmp_path, "")
    cfg = Config.load(tmp_path)
    assert cfg.entries_dir == tmp_path.resolve() / ".memory" / "entries"
    assert cfg.modules_path == tmp_path.resolve() / ".memory" / "modules.yaml"
    assert cfg.cache_dir.parent == tmp_path / "cache"
    assert cfg.cache_dir == Config.load(tmp_path).cache_dir
