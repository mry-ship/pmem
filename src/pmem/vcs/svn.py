from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from pmem.vcs.base import VCS, run_tool

_UNCOMMITTED = {"unversioned", "added", "modified", "replaced"}
_CODES = {
    "unversioned": "?",
    "added": "A",
    "modified": "M",
    "replaced": "R",
    "deleted": "D",
    "normal": "",
    "missing": "!",
    "conflicted": "C",
}


class SvnVCS(VCS):
    name = "svn"

    def _xml(self, *args: str) -> ET.Element | None:
        proc = run_tool(["svn", *args, "--xml", "--non-interactive"], self.root)
        if proc.returncode != 0:
            return None
        try:
            return ET.fromstring(proc.stdout)
        except ET.ParseError:
            return None

    def revision(self) -> str:
        info = self._xml("info", str(self.root))
        entry = info.find("entry") if info is not None else None
        rev = entry.get("revision") if entry is not None else None
        return f"svn:r{rev}" if rev else "none"

    def _item_status(self, path: Path) -> str | None:
        status = self._xml("status", "--depth", "empty", str(path))
        if status is None:
            return None
        node = status.find("./target/entry/wc-status")
        if node is not None:
            return node.get("item")
        return "normal" if self._xml("info", str(path)) is not None else "unversioned"

    def status_code(self, path: Path) -> str:
        item = self._item_status(path)
        return _CODES.get(item or "", "?")

    def is_uncommitted(self, path: Path) -> bool:
        item = self._item_status(path)
        return item is None or item in _UNCOMMITTED

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        if not folder.is_dir():
            return 0
        # 目录本身未纳入版本库时，svn status 只给警告、不列出其中文件
        if self._xml("info", str(folder)) is None:
            return sum(1 for _ in folder.rglob(f"*{suffix}"))
        status = self._xml("status", str(folder))
        if status is None:
            return None
        count = 0
        for entry in status.iter("entry"):
            node = entry.find("wc-status")
            if node is None or node.get("item") not in _UNCOMMITTED:
                continue
            path = Path(entry.get("path") or "")
            if not path.is_absolute():
                path = self.root / path
            if path.is_dir():
                if node.get("item") == "unversioned":
                    count += sum(1 for _ in path.rglob(f"*{suffix}"))
            elif path.name.endswith(suffix):
                count += 1
        return count

    def add(self, path: Path) -> None:
        run_tool(["svn", "add", "--parents", "-q", "--non-interactive", str(path)], self.root)
