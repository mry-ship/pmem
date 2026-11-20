"""pyright 基础模式覆盖 core / index / service / catalog（v0.7 §3.6）。"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyright_basic_on_core_index_service_catalog():
    pyright = shutil.which("pyright")
    cmd = [pyright] if pyright else [sys.executable, "-m", "pyright"]
    result = subprocess.run(
        [*cmd, "--project", str(ROOT / "pyrightconfig.json")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return
    # 未安装时提示装开发依赖，避免把缺包当成类型错误
    combined = (result.stdout or "") + (result.stderr or "")
    if "No module named pyright" in combined or "不是内部或外部命令" in combined:
        pytest_skip = __import__("pytest").skip
        pytest_skip("未安装 pyright：uv sync --group dev")
    assert False, f"pyright 未通过（exit {result.returncode}）：\n{combined[-4000:]}"
