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

    def add(self, path: Path) -> None:
        run_tool(["svn", "add", "--parents", "-q", "--non-interactive", str(path)], self.root)
