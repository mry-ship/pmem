from __future__ import annotations

import getpass
import os
import subprocess
from datetime import date
from pathlib import Path


def run_tool(args: list[str], cwd: Path, timeout: float = 30) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, check=False)


def fallback_user() -> str:
    if env := os.environ.get("PMEM_AUTHOR"):
        return env
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return "unknown"


class VCS:
    """版本控制适配接口；子类覆盖需要的方法。"""

    name = "none"
    # dirty_files 是否便宜到可以每次调用（Git 走索引，几十毫秒；SVN 要遍历整个工作副本，大仓库要几秒）
    cheap_dirty_files = False

    def __init__(self, root: Path):
        self.root = root

    def revision(self) -> str:
        return "none"

    def current_user(self) -> str:
        return fallback_user()

    def is_uncommitted(self, path: Path) -> bool:
        return True

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        """folder 下未提交（新增/修改/未纳入版本库）的文件数；不在版本控制下返回 None。"""
        return None

    def add(self, path: Path) -> None:
        return None

    def move(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)

    def file_at(self, rel: str, day: str) -> str | None:
        """day（YYYY-MM-DD）当天结束时已提交的文件内容；不支持或取不到时返回 None。"""
        return None

    def dirty_files(self) -> list[str] | None:
        """项目里相对版本库有改动、已删除或未纳入版本库（且未被忽略）的文件，路径相对项目根；不支持时返回 None。"""
        return None

    def changed_after(self, paths: list[str], since: str) -> dict[str, str]:
        """since（YYYY-MM-DD）之后有改动的文件 → 最近改动日期；含未提交的修改（记为今天）。

        paths 为相对项目根的路径。没有版本库时按文件修改时间判断。
        """
        found: dict[str, str] = {}
        for rel in paths:
            path = self.root / rel
            if path.is_file():
                day = date.fromtimestamp(path.stat().st_mtime).isoformat()
                if day > since:
                    found[rel] = day
        return found
