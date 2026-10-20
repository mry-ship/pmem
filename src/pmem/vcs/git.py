from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from pmem.vcs.base import HISTORY_TIMEOUT, VCS, fallback_user, file_mtime, path_batches, run_tool


def _iso(moment: float) -> str:
    """git 的 --since/--before 参数：UTC 时间，精确到秒（含这一秒）。
    Windows 上 1970 年附近的时间戳转本地时间会抛 OSError，所以用 UTC 并且不早于 1970-01-02。"""
    return datetime.fromtimestamp(max(int(moment), 86400), tz=timezone.utc).isoformat(timespec="seconds")


class GitVCS(VCS):
    name = "git"
    cheap_dirty_files = True

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

    def file_before(self, rel: str, moment: float) -> str | None:
        rev = self._git("rev-list", "-1", f"--before={_iso(moment)}", "HEAD", "--", rel)
        if not rev:
            return None
        # ./ 让路径相对项目根解析（项目可能是仓库的子目录）
        proc = run_tool(["git", "show", f"{rev}:./{rel}"], self.root)
        return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else None

    def is_committed(self, path: Path) -> bool:
        return bool(self._git("log", "-1", "--format=%h", "--", str(path)))

    def commit_times(self, paths: list[str], since: float) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        for batch in path_batches(paths):
            # 一次 git log 拿到这批文件在 since 之后的提交；--relative 让输出相对项目根（可能是仓库子目录）
            out = self._git("log", f"--since={_iso(since)}", "--format=@%ct", "--name-only", "--relative", "--",
                            *batch)
            moment = 0.0
            for line in (out or "").splitlines():
                if line.startswith("@"):
                    moment = float(line[1:].strip() or 0)
                elif line.strip() and moment > since:
                    found.setdefault(line.strip(), []).append(moment)
        wanted = {p.replace("\\", "/") for p in paths}
        return {k: sorted(v) for k, v in found.items() if k in wanted}

    def changed_since(self, paths: list[str], since: float) -> dict[str, float]:
        if not paths:
            return {}
        found = {rel: times[-1] for rel, times in self.commit_times(paths, since).items()}
        now = time.time()
        for batch in path_batches(paths):
            # status --porcelain 的路径总是相对仓库根，这里用 diff --relative 保持与项目根一致
            dirty = self._git("diff", "HEAD", "--name-only", "--relative", "--", *batch) or ""
            for rel in (r.strip() for r in dirty.splitlines()):
                # 未提交的修改按文件修改时间算：写记忆之前就改好、还没提交的代码不算“之后改过”
                moment = file_mtime(self.root / rel) or now
                if rel and moment > since:
                    found[rel] = max(found.get(rel, 0.0), moment)
        wanted = {p.replace("\\", "/") for p in paths}
        return {k: v for k, v in found.items() if k in wanted}

    def commits_since(self, since: str) -> list[tuple[str, list[str]]]:
        # --relative：项目可能是仓库的子目录，路径要相对项目根
        # 只给日期时 git 用当前时刻补齐，会漏掉起始日较早的提交
        args = ["git", "-c", "core.quotepath=off", "log", f"--since={since} 00:00", "--name-only", "--relative",
                "--pretty=format:@@%ci"]
        try:
            proc = run_tool(args, self.root, timeout=HISTORY_TIMEOUT)
        except subprocess.TimeoutExpired:
            return []
        if proc.returncode != 0:
            return []
        commits = []
        for block in proc.stdout.decode("utf-8", errors="replace").split("@@")[1:]:
            lines = [f.strip() for f in block.splitlines() if f.strip()]
            if lines:
                commits.append((lines[0][:10], lines[1:]))
        return commits

    def dirty_files(self) -> list[str] | None:
        # ls-files 的输出相对当前目录，项目是仓库子目录时也直接相对项目根
        proc = run_tool(["git", "ls-files", "-m", "-d", "-o", "--exclude-standard", "-z"], self.root)
        if proc.returncode != 0:
            return None
        return list(dict.fromkeys(p for p in proc.stdout.decode("utf-8", errors="replace").split("\0") if p))

    def uncommitted_count(self, folder: Path, suffix: str = ".md") -> int | None:
        out = self._git("status", "--porcelain", "--untracked-files=all", "--", str(folder))
        if out is None:
            return None
        return sum(1 for line in out.splitlines() if line.rstrip().strip('"').endswith(suffix))
