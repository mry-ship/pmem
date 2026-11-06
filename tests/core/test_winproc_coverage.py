"""生产代码凡调 subprocess.run/Popen，Windows 上必须藏窗，防止以后再漏。"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "pmem"


def _call_is_guarded(node: ast.Call, lines: list[str]) -> bool:
    """creationflags / **no_window_kwargs()，或邻近窗口里已写 CREATE_NO_WINDOW / DETACHED。"""
    for kw in node.keywords:
        if kw.arg == "creationflags":
            return True
        if kw.arg is None:
            # **no_window_kwargs() 或 **某个 dict
            if isinstance(kw.value, ast.Call) and isinstance(kw.value.func, ast.Name):
                if kw.value.func.id == "no_window_kwargs":
                    return True
            if isinstance(kw.value, ast.Name) and "no_window" in kw.value.id:
                return True
    start = max(0, node.lineno - 30)
    end = min(len(lines), (node.end_lineno or node.lineno))
    window = "\n".join(lines[start:end])
    return "CREATE_NO_WINDOW" in window or "no_window_kwargs" in window or "DETACHED_PROCESS" in window


def test_all_production_subprocess_calls_hide_console_on_windows():
    missing: list[str] = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr in {"run", "Popen", "call", "check_output", "check_call"}):
                continue
            if not (isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
                continue
            if _call_is_guarded(node, lines):
                continue
            rel = path.relative_to(SRC).as_posix()
            missing.append(f"{rel}:{node.lineno} subprocess.{func.attr}")
    assert not missing, "漏加 CREATE_NO_WINDOW / no_window_kwargs：\n" + "\n".join(missing)
