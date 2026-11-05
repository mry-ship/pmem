"""Windows doctor should flag console python hook launchers; pyw/pythonw are fine."""
from __future__ import annotations

from pmem.cli.doctor_cmd import _is_console_python_hook, _iter_hook_commands


def test_console_python_hook_detection():
    assert _is_console_python_hook("python3 pmem_art.py hook pre-gen")
    assert _is_console_python_hook("python pmem_art.py hook stop")
    assert _is_console_python_hook("py -3 pmem_art.py hook post-asset")
    assert not _is_console_python_hook("pyw -3 -u pmem_art.py hook pre-gen")
    assert not _is_console_python_hook("pythonw -u pmem_art.py hook stop")
    assert not _is_console_python_hook("pmemw hook pre-tool")


def test_iter_hook_commands_flat_and_nested():
    flat = {
        "hooks": {
            "preToolUse": [{"command": "python3 a.py hook x"}],
            "stop": [{"command": "pmemw hook stop"}],
        }
    }
    assert _iter_hook_commands(flat) == ["python3 a.py hook x", "pmemw hook stop"]
    nested = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "GenerateImage",
                    "hooks": [{"type": "command", "command": "py -3 a.py hook y"}],
                }
            ]
        }
    }
    assert _iter_hook_commands(nested) == ["py -3 a.py hook y"]
