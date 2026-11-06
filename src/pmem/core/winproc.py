"""Windows 子进程窗口控制。Hook/后台热路径调 git 等 CUI 时用，避免弹黑框。"""
from __future__ import annotations

import subprocess
import sys


def no_window_kwargs() -> dict:
    """Windows 上禁止为控制台子进程分配新控制台；其它平台返回空字典。不改变命令语义。"""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}
