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
    # 完整路径的控制台 python 也要认（^python 锚串首会漏）
    assert _is_console_python_hook(r"C:\Python312\python.exe pmem_art.py hook stop")
    assert _is_console_python_hook(r'"C:\Program Files\Python312\python.exe" pmem_art.py hook x')
    assert _is_console_python_hook("/usr/bin/python3 a.py hook y")
    # 带小版本号的解释器也要认（python3.12 / python3.11）
    assert _is_console_python_hook("python3.12 a.py hook x")
    assert _is_console_python_hook(r"C:\Python311\python3.11.exe a.py hook y")
    # 完整路径的 pythonw 仍不算（不弹框），含版本号的 pythonw 也不算
    assert not _is_console_python_hook(r"C:\Python312\pythonw.exe a.py hook z")
    assert not _is_console_python_hook("pythonw3.12 a.py")
    # basename 里含 python 但不是解释器的程序不要误报
    assert not _is_console_python_hook("mypython-wrapper a.py")
    # 单引号路径、PowerShell 调用符、cmd /c 后面的控制台 python 也要认
    assert _is_console_python_hook(r"'C:\Python312\python.exe' a.py hook x")
    assert _is_console_python_hook(r"'C:\Program Files\Python312\python.exe' a.py hook x")
    assert _is_console_python_hook(r'& "C:\Python312\python.exe" a.py hook x')
    assert _is_console_python_hook("cmd /c python a.py hook x")
    assert _is_console_python_hook(r'cmd /c "C:\Program Files\Python312\python.exe" a.py')
    assert _is_console_python_hook('cmd /c "python a.py hook x"')
    assert not _is_console_python_hook(r"& 'C:\Python312\pythonw.exe' a.py")


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
