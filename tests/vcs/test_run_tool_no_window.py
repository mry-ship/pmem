"""Windows Hook 热路径：run_tool / 共用 winproc 必须带 CREATE_NO_WINDOW，避免 git/svn 弹控制台。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pmem.core import winproc
from pmem.vcs.base import run_tool


def test_no_window_kwargs_only_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert winproc.no_window_kwargs() == {"creationflags": subprocess.CREATE_NO_WINDOW}
    monkeypatch.setattr(sys, "platform", "linux")
    assert winproc.no_window_kwargs() == {}


def test_run_tool_passes_create_no_window_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_tool(["git", "rev-parse", "HEAD"], tmp_path)
    assert seen.get("creationflags") == subprocess.CREATE_NO_WINDOW
    assert seen.get("capture_output") is True


def test_run_tool_omits_creationflags_off_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_tool(["git", "rev-parse", "HEAD"], Path(tmp_path))
    assert "creationflags" not in seen
