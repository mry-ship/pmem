from __future__ import annotations

from pathlib import Path

from pmem.vcs.base import VCS, fallback_user, run_tool


class GitVCS(VCS):
    name = "git"

    def _git(self, *args: str) -> str | None:
        proc = run_tool(["git", "-c", "core.quotepath=off", *args], self.root)
        if proc.returncode != 0:
            return None
        return proc.stdout.decode("utf-8", errors="replace").strip()

    def revision(self) -> str:
        short = self._git("rev-parse", "--short", "HEAD")
        return f"git:{short}" if short else "none"

    def current_user(self) -> str:
        return self._git("config", "user.name") or fallback_user()

    def is_uncommitted(self, path: Path) -> bool:
        out = self._git("status", "--porcelain", "--untracked-files=all", "--", str(path))
        return bool(out)

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        out = self._git("status", "--porcelain", "--untracked-files=all", "--", str(folder))
        if out is None:
            return None
        return sum(1 for line in out.splitlines() if line.rstrip().strip('"').endswith(suffix))
