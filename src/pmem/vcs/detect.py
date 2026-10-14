from __future__ import annotations

from pathlib import Path

from pmem.vcs.base import VCS
from pmem.vcs.git import GitVCS
from pmem.vcs.svn import SvnVCS

_KINDS = {"git": GitVCS, "svn": SvnVCS, "none": VCS}


def _find_marker(root: Path) -> str | None:
    for candidate in (root, *root.parents):
        if (candidate / ".git").exists():
            return "git"
        if (candidate / ".svn").is_dir():
            return "svn"
    return None


def detect_vcs(root: str | Path, setting: str = "auto") -> VCS:
    root = Path(root).resolve()
    if setting not in ("auto", *_KINDS):
        raise ValueError(f"配置项 vcs 只能是 auto / git / svn / none，当前为 {setting!r}")
    kind = (_find_marker(root) or "none") if setting == "auto" else setting
    return _KINDS[kind](root)
