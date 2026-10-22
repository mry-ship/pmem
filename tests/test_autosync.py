import os
import sys
import time
from pathlib import Path

import pytest
import yaml

from pmem.catalog.autosync import run_auto
from pmem.core import autosync
from pmem.core.config import Config
from pmem.hooks.gate import handle

CONFIG = "project: {{ name: demo }}\nvcs: none\nembedding: {{ backend: none }}\nwiki: {{ auto: false }}\n{extra}"
MODULES = """\
# 模块目录
categories: { gameplay: {}, infra: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Game/Jigsaw/**] }
"""


def _write(root: Path, rel: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text("class X {}\n", encoding="utf-8")


@pytest.fixture
def make(tmp_path):
    def build(extra: str = "", modules: str = MODULES) -> Path:
        root = tmp_path / "proj"
        (root / ".memory").mkdir(parents=True, exist_ok=True)
        (root / ".memory" / "config.yaml").write_text(CONFIG.format(extra=extra), encoding="utf-8")
        (root / ".memory" / "modules.yaml").write_text(modules, encoding="utf-8")
        _write(root, "src/Game/Jigsaw/Board.cs")
        for name in ("A", "B", "C"):
            _write(root, f"src/Game/Match/{name}.cs")
        return root

    return build


def _modules(root: Path) -> dict:
    return yaml.safe_load((root / ".memory" / "modules.yaml").read_text(encoding="utf-8"))["modules"]


def test_apply_registers_new_directories_and_keeps_header(make):
    root = make()
    result = run_auto(root, "session")
    assert result["status"] == "found" and result["applied"] is True
    assert _modules(root)["gameplay.Match"]["paths"] == ["src/Game/Match/**"]
    assert (root / ".memory" / "modules.yaml").read_text(encoding="utf-8").startswith("# 模块目录")
    notice = autosync.take_notice(Config.load(root).cache_dir)
    assert "已自动登记" in notice and "gameplay.Match" in notice and "pmem migrate rename" in notice
    assert autosync.take_notice(Config.load(root).cache_dir) is None


def test_unchanged_directories_skip_planning_until_full_scan_is_due(make):
    root = make()
    run_auto(root, "session")
    assert run_auto(root, "session")["status"] == "unchanged"
    _write(root, "src/Game/Tiny/X.cs")
    second = run_auto(root, "edit")
    assert second["status"] == "found" and "gameplay.Tiny" in second["new_candidates"]
    assert run_auto(root, "full")["status"] == "clean"


def test_remind_mode_leaves_modules_yaml_alone(make):
    root = make("sync: { auto: remind }\n")
    before = (root / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    result = run_auto(root, "session")
    assert result["status"] == "found" and result["applied"] is False
    assert (root / ".memory" / "modules.yaml").read_text(encoding="utf-8") == before
    assert "pmem sync --apply" in autosync.take_notice(Config.load(root).cache_dir)


def test_body_comments_fall_back_to_reminding(make):
    root = make(modules=MODULES + "  # 正文里的注释，重写会丢\n")
    result = run_auto(root, "session")
    assert result["applied"] is False and result["skipped"] == "comments"
    assert "注释" in autosync.take_notice(Config.load(root).cache_dir)


def test_off_does_nothing(make):
    root = make("sync: { auto: off }\n")
    assert run_auto(root, "session") == {"status": "off"}
    assert "gameplay.Match" not in _modules(root)


def test_bad_sync_config_is_rejected(make):
    from pmem.core.config import ConfigError

    with pytest.raises(ConfigError):
        Config.load(make("sync: { auto: yes-please }\n"))


@pytest.fixture
def spawned(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append(cmd)

    monkeypatch.delenv("PMEM_NO_AUTOSYNC", raising=False)
    monkeypatch.setattr(autosync.subprocess, "Popen", FakePopen)
    return calls


def _edited(root: Path, rel: str, conv: str = "c1") -> None:
    handle("edited", {"conversation_id": conv, "file_path": str(root / rel)}, root)


def test_editing_unregistered_code_spawns_one_background_scan(make, spawned):
    root = make()
    _edited(root, "src/Game/Jigsaw/Board.cs")
    _edited(root, "README.md")
    assert spawned == []
    _write(root, "src/Game/Shop/Shop.cs")
    _edited(root, "src/Game/Shop/Shop.cs")
    _edited(root, "src/Game/Shop/Shop.cs")
    assert len(spawned) == 1 and spawned[0][-4:] == ["--auto", "edit", "--root", str(root)]


def test_session_start_spawns_by_interval(make, spawned):
    root = make()
    handle("session", {"conversation_id": "c1"}, root)
    handle("session", {"conversation_id": "c2"}, root)
    assert len(spawned) == 1 and "session" in spawned[0]
    cache = Config.load(root).cache_dir
    state = autosync.load_state(cache)
    state["last_spawn"] = time.time() - 31 * 60
    autosync.save_state(cache, state)
    handle("session", {"conversation_id": "c3"}, root)
    assert len(spawned) == 2


def test_running_scan_blocks_new_spawns(make, spawned):
    root = make()
    cache = Config.load(root).cache_dir
    with autosync.scan_lock(cache) as locked:
        assert locked
        handle("session", {"conversation_id": "c1"}, root)
        assert run_auto(root, "session") == {"status": "busy"}
    assert spawned == []


def test_post_tool_carries_the_notice_once(make):
    root = make()
    run_auto(root, "session")
    read = {"conversation_id": "c1", "tool_name": "Read", "tool_input": {"path": str(root / "README.md")}}
    assert "gameplay.Match" in handle("post-tool", read, root).get("additional_context", "")
    assert "gameplay.Match" not in handle("post-tool", read, root).get("additional_context", "")


@pytest.mark.skipif(sys.platform != "win32" and not hasattr(os, "fork"), reason="需要能拉起子进程")
def test_real_background_process_registers_the_directory(make, monkeypatch):
    root = make()
    monkeypatch.delenv("PMEM_NO_AUTOSYNC", raising=False)
    monkeypatch.setenv("PMEM_NO_EVENTS", "1")
    assert autosync.spawn(root, Config.load(root).cache_dir, "session")
    deadline = time.time() + 60
    while time.time() < deadline and "gameplay.Match" not in _modules(root):
        time.sleep(0.2)
    assert "gameplay.Match" in _modules(root)
    while time.time() < deadline and autosync.lock_busy(Config.load(root).cache_dir):
        time.sleep(0.2)
