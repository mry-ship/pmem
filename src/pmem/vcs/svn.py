from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from pmem.vcs.base import HISTORY_TIMEOUT, VCS, path_batches, run_tool

_UNCOMMITTED = {"unversioned", "added", "modified", "replaced"}
_DIRTY = _UNCOMMITTED | {"deleted", "missing", "conflicted"}
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

    def _xml(self, *args: str, partial: bool = False) -> ET.Element | None:
        proc = run_tool(["svn", *args, "--xml", "--non-interactive"], self.root)
        if proc.returncode != 0 and not (partial and proc.stdout.strip()):
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

    def is_committed(self, path: Path) -> bool:
        item = self._item_status(path)
        return item is not None and item not in ("unversioned", "added")

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

    def changed_after(self, paths: list[str], since: str) -> dict[str, str]:
        if not paths:
            return {}
        found: dict[str, str] = {}
        today = date.today().isoformat()
        for batch in path_batches(paths):
            # svn info 读本地工作副本元数据，不访问服务器；commit/date 是该文件最后一次提交的时间（UTC）
            # 有路径未纳入版本库时退出码非 0，但其余路径的 XML 仍完整输出
            info = self._xml("info", *batch, partial=True)
            for entry in info.iter("entry") if info is not None else []:
                node = entry.find("commit/date")
                rel = (entry.get("path") or "").replace("\\", "/")
                day = (node.text or "")[:10] if node is not None else ""
                if rel and day > since:
                    found[rel] = day
            status = self._xml("status", *batch, partial=True)
            for entry in status.iter("entry") if status is not None else []:
                node = entry.find("wc-status")
                if node is not None and node.get("item") in ("modified", "replaced") and today > since:
                    found[(entry.get("path") or "").replace("\\", "/")] = today
        wanted = {p.replace("\\", "/") for p in paths}
        return {k: v for k, v in found.items() if k in wanted}

    def dirty_files(self) -> list[str] | None:
        # 只读本地工作副本，不访问服务器；未纳入版本库的目录展开成其中的文件
        status = self._xml("status", "--ignore-externals", str(self.root))
        if status is None:
            return None
        files: list[str] = []
        for entry in status.iter("entry"):
            node = entry.find("wc-status")
            if node is None or node.get("item") not in _DIRTY:
                continue
            path = Path(entry.get("path") or "")
            if not path.is_absolute():
                path = self.root / path
            found = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
            for item in found:
                try:
                    files.append(item.relative_to(self.root).as_posix())
                except ValueError:
                    continue
        return list(dict.fromkeys(files))

    def commits_since(self, since: str) -> list[tuple[str, list[str]]]:
        info = self._xml("info", str(self.root))
        rel = info.findtext("./entry/relative-url") if info is not None else None
        rel = rel or "^/"
        prefix = rel[1:].rstrip("/") + "/" if rel.startswith("^") else "/"
        # svn log 要访问服务器，可能较慢
        args = ["svn", "log", "-v", "--xml", "--non-interactive", "-l", "2000", "-r", f"HEAD:{{{since}}}", str(self.root)]
        try:
            proc = run_tool(args, self.root, timeout=HISTORY_TIMEOUT)
            if proc.returncode != 0:
                return []
            log = ET.fromstring(proc.stdout)
        except (subprocess.TimeoutExpired, ET.ParseError):
            return []
        commits = []
        for entry in log.iter("logentry"):
            paths = [p.text or "" for p in entry.iter("path") if p.get("kind") != "dir" and not p.get("copyfrom-path")]
            commits.append(((entry.findtext("date") or "")[:10], [p[len(prefix):] for p in paths if p.startswith(prefix)]))
        return commits

    def add(self, path: Path) -> None:
        run_tool(["svn", "add", "--parents", "-q", "--non-interactive", str(path)], self.root)

    def move(self, src: Path, dst: Path) -> None:
        # 已纳入版本库的用 svn mv 保留历史；未纳入的照常移动，保持未纳入
        if self._item_status(src) in (None, "unversioned"):
            super().move(src, dst)
            return
        proc = run_tool(["svn", "mv", "--parents", "-q", "--non-interactive", str(src), str(dst)], self.root)
        if proc.returncode != 0:
            raise OSError(proc.stderr.decode("utf-8", errors="replace").strip() or f"svn mv {src} 失败")
