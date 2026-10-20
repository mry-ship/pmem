from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path


def run_tool(args: list[str], cwd: Path, timeout: float = 30) -> subprocess.CompletedProcess[bytes]:
    """git/svn 不在 PATH、工作目录不存在或超时，都当作命令失败（返回码 127），由调用方按“查不出”处理，不抛异常。"""
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, b"", str(exc).encode("utf-8", errors="replace"))


MAX_ARGS_CHARS = 8000
HISTORY_TIMEOUT = 120.0


def path_batches(paths: list[str], limit: int = MAX_ARGS_CHARS) -> list[list[str]]:
    """按总长度切分路径参数：Windows 命令行上限约 32K 字符，记忆多了一次传完会直接失败。"""
    batches: list[list[str]] = [[]]
    size = 0
    for path in paths:
        if batches[-1] and size + len(path) + 1 > limit:
            batches.append([])
            size = 0
        batches[-1].append(path)
        size += len(path) + 1
    return batches if batches[0] else []


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

    def is_committed(self, path: Path) -> bool | None:
        """文件是否已有提交记录；之后在工作区里改过也算（确认、归档会改写已提交的记忆）。
        版本库命令出错、判断不了时返回 None，调用方按“可能已提交”处理。"""
        return False

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        """folder 下未提交（新增/修改/未纳入版本库）的文件数；不在版本控制下返回 None。"""
        return None

    def add(self, path: Path) -> None:
        return None

    def move(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)

    def file_before(self, rel: str, moment: float) -> str | None:
        """moment（Unix 秒）时已提交的文件内容；不支持或取不到时返回 None。"""
        return None

    def commits_after(self, revision: str, paths: list[str]) -> dict[str, list[tuple[str, float]]]:
        """当前版本有、revision（revision() 的返回值去掉 "git:" 这类前缀）没有的提交：文件 → [(提交号, 提交时刻)]。
        拉取、合并进来的提交可能早于 revision 的时间，按时间比较会漏掉。不支持或 revision 已不存在时返回空。"""
        return {}

    def file_in_commit(self, commit: str, rel: str) -> str | None:
        """某次提交里的文件内容；文件不存在或取不到时返回 None。"""
        return None

    def dirty_files(self) -> list[str] | None:
        """项目里相对版本库有改动、已删除或未纳入版本库（且未被忽略）的文件，路径相对项目根；不支持时返回 None。"""
        return None

    def commits_since(self, since: str) -> list[tuple[str, list[str]]]:
        """since（YYYY-MM-DD）以来的每次提交：(提交日期, 改动的文件)，路径相对项目根；取不到时返回空列表。"""
        return []

    def changed_since(self, paths: list[str], since: float) -> dict[str, float]:
        """since（Unix 秒）之后有改动的文件 → 最近一次改动的时刻；未提交的修改取文件修改时间。

        paths 为相对项目根的路径。没有版本库时按文件修改时间判断。
        """
        found: dict[str, float] = {}
        for rel in paths:
            moment = file_mtime(self.root / rel)
            if moment is not None and moment > since:
                found[rel] = moment
        return found

    def commit_times(self, paths: list[str], since: float) -> dict[str, list[float]]:
        """since 之后每个文件的提交时刻（从早到晚）；未提交的改动不算。没有版本库时取文件修改时间。"""
        return {rel: [moment] for rel, moment in self.changed_since(paths, since).items()}


def file_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime if path.is_file() else None
    except OSError:
        return None
