from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from pmem.cli.doctor_cmd import (
    DOCTOR_INTERVAL_HOURS,
    consume_doctor_tip,
    is_doctor_due,
    maybe_lazy_doctor_on_hook,
    run_doctor,
    save_doctor_state,
    try_claim_lazy_doctor,
)
from pmem.cli.main import main
from pmem.core.config import Config
from pmem.hooks.gate import handle


def _project(tmp_path: Path) -> Path:
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    config = tmp_path / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("backend: auto", "backend: none"), encoding="utf-8")
    return tmp_path


def test_default_interval_is_24h():
    assert DOCTOR_INTERVAL_HOURS == 24.0


def test_due_when_missing_state(tmp_path):
    assert is_doctor_due(tmp_path / "cache")


def test_not_due_within_24h(tmp_path):
    cache = tmp_path / "cache"
    save_doctor_state(cache, {"last_run": 1e18, "status": "ok"})
    assert not is_doctor_due(cache, now=1e18 + 60)


def test_due_after_24h(tmp_path):
    cache = tmp_path / "cache"
    save_doctor_state(cache, {"last_run": 1000.0, "status": "ok"})
    assert is_doctor_due(cache, now=1000.0 + 24 * 3600)


def test_claim_blocks_double_spawn(tmp_path):
    cache = tmp_path / "cache"
    assert try_claim_lazy_doctor(cache, now=10.0)
    assert not try_claim_lazy_doctor(cache, now=11.0)


def test_quiet_writes_state_and_stays_silent(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("PMEM_NO_LAZY_DOCTOR", raising=False)
    root = _project(tmp_path)
    capsys.readouterr()
    assert main(["doctor", "--quiet", "--source", "unit", "--root", str(root)]) == 0
    assert capsys.readouterr().out.strip() == ""
    cache = Config.load(root).cache_dir
    state = json.loads((cache / "last_doctor.json").read_text(encoding="utf-8"))
    assert state["source"] == "unit"
    assert state["status"] == "ok"
    assert state["inspect_only"] is True
    modules = (root / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    assert "modules:" in modules


def test_quiet_does_not_change_modules_or_entries(tmp_path, monkeypatch):
    monkeypatch.delenv("PMEM_NO_LAZY_DOCTOR", raising=False)
    root = _project(tmp_path)
    entries = root / ".memory" / "entries"
    entries.mkdir(exist_ok=True)
    before_mod = (root / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    before_entries = {p.name: p.read_text(encoding="utf-8") for p in entries.rglob("*.md")}
    run_doctor(root, quiet=True, source="safe")
    assert (root / ".memory" / "modules.yaml").read_text(encoding="utf-8") == before_mod
    assert {p.name: p.read_text(encoding="utf-8") for p in entries.rglob("*.md")} == before_entries


def test_spawn_events_claim(tmp_path, monkeypatch):
    monkeypatch.delenv("PMEM_NO_LAZY_DOCTOR", raising=False)
    root = _project(tmp_path)
    cache = Config.load(root).cache_dir
    for event in ("session", "pre-tool", "post-tool", "stop", "prompt", "edited"):
        save_doctor_state(cache, {})
        (cache / "last_doctor.claim").unlink(missing_ok=True)
        with mock.patch("pmem.cli.doctor_cmd.spawn_lazy_doctor", return_value=True) as sp:
            maybe_lazy_doctor_on_hook(root, event, cache)
        sp.assert_called_once()


def test_unknown_event_does_not_spawn(tmp_path, monkeypatch):
    monkeypatch.delenv("PMEM_NO_LAZY_DOCTOR", raising=False)
    root = _project(tmp_path)
    cache = Config.load(root).cache_dir
    with mock.patch("pmem.cli.doctor_cmd.spawn_lazy_doctor") as sp:
        maybe_lazy_doctor_on_hook(root, "compact", cache)
    sp.assert_not_called()


def test_pre_tool_and_stop_do_not_eat_pending_tip(tmp_path, monkeypatch):
    monkeypatch.delenv("PMEM_NO_LAZY_DOCTOR", raising=False)
    root = _project(tmp_path)
    cache = Config.load(root).cache_dir
    save_doctor_state(cache, {
        "last_run": 1e18,
        "tip_pending": True,
        "needs_attention": True,
        "tip_line": "🩺 记忆医生：覆盖率 10%（可 pmem doctor）",
    })
    with mock.patch("pmem.cli.doctor_cmd.spawn_lazy_doctor"):
        assert maybe_lazy_doctor_on_hook(root, "pre-tool", cache) is None
        assert maybe_lazy_doctor_on_hook(root, "stop", cache) is None
        assert maybe_lazy_doctor_on_hook(root, "prompt", cache) is None
        tip = maybe_lazy_doctor_on_hook(root, "post-tool", cache)
    assert tip.startswith("🩺 记忆医生")


def test_env_skips_spawn(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_NO_LAZY_DOCTOR", "1")
    root = _project(tmp_path)
    cache = Config.load(root).cache_dir
    with mock.patch("pmem.cli.doctor_cmd.spawn_lazy_doctor") as sp:
        assert maybe_lazy_doctor_on_hook(root, "session", cache) is None
    sp.assert_not_called()


def test_tip_once_per_day(tmp_path):
    cache = tmp_path / "cache"
    save_doctor_state(cache, {
        "tip_pending": True,
        "needs_attention": True,
        "tip_line": "🩺 记忆医生：覆盖率 10%（可 pmem doctor）",
    })
    assert consume_doctor_tip(cache, now=1_700_000_000).startswith("🩺 记忆医生")
    assert consume_doctor_tip(cache, now=1_700_000_000) is None


def test_session_hook_does_not_dump_doctor_report(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_NO_LAZY_DOCTOR", "1")
    root = _project(tmp_path)
    out = handle("session", {"conversation_id": "c1"}, root)
    msg = json.dumps(out, ensure_ascii=False)
    assert "自检完成" not in msg
    assert "lifecycle_mode" not in msg
    assert "未覆盖：" not in msg
    assert out == {}
