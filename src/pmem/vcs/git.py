from __future__ import annotations

from datetime import date, timedelta
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

    def changed_after(self, paths: list[str], since: str) -> dict[str, str]:
        if not paths:
            return {}
        found: dict[str, str] = {}
        start = (date.fromisoformat(since) + timedelta(days=1)).isoformat()
        # 一次 git log 拿到所有文件在 since 之后的提交；--relative 让输出相对项目根（可能是仓库子目录）
        out = self._git("log", f"--since={start} 00:00", "--format=@%cs", "--name-only", "--relative", "--", *paths)
        day = ""
        for line in (out or "").splitlines():
            if line.startswith("@"):
                day = line[1:].strip()
            elif line.strip() and day > since:
                found.setdefault(line.strip(), day)
        # status --porcelain 的路径总是相对仓库根，这里用 diff --relative 保持与项目根一致
        dirty = self._git("diff", "HEAD", "--name-only", "--relative", "--", *paths) or ""
        today = date.today().isoformat()
        for rel in dirty.splitlines():
            if rel.strip() and today > since:
                found[rel.strip()] = today
        wanted = {p.replace("\\", "/") for p in paths}
        return {k: v for k, v in found.items() if k in wanted}

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        out = self._git("status", "--porcelain", "--untracked-files=all", "--", str(folder))
        if out is None:
            return None
        return sum(1 for line in out.splitlines() if line.rstrip().strip('"').endswith(suffix))
