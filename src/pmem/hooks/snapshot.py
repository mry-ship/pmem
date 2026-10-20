"""终端命令的事后核对：事前解析不出写入目标时，比对执行前后的未提交文件。"""

from __future__ import annotations

import hashlib
import time

from pmem.hooks.payload import tool_input
from pmem.hooks.shell import VARIABLE_PATH, WILDCARD_PATH, may_change_unseen, scan

MAX_PENDING_SNAPSHOTS = 8
SLOW_SNAPSHOT_SECONDS = 1.0
SLOW_SNAPSHOT_PAUSE = 24 * 3600
SLOW_SNAPSHOT_MARK = "snapshot-slow"


def command_key(command: str) -> str:
    return "cmd:" + hashlib.sha1(command.encode("utf-8", "replace")).hexdigest()[:16]


def needs_snapshot(command: str, base: str) -> bool:
    """脚本、内联代码、变量拼出来的路径和不认识的程序（格式化、git stash 等）事前看不出写了什么，
    放行时记下快照，执行后比对未提交文件，见 Gate._shell_after。"""
    targets, runs_code = scan(command, base)
    return (runs_code or any(VARIABLE_PATH.search(t) or WILDCARD_PATH.search(t) for t in targets)
            or may_change_unseen(command))


class Snapshots:
    def _dirty_snapshot(self, paused_ok: bool = True) -> dict[str, list[int]] | None:
        # 大型工作副本（尤其 SVN）列未提交文件可能要好几秒；慢过一次就当天不再做，免得拖慢每条终端命令
        slow = self.config.cache_dir / SLOW_SNAPSHOT_MARK
        try:
            if paused_ok and slow.exists() and time.time() - slow.stat().st_mtime < SLOW_SNAPSHOT_PAUSE:
                return None
        except OSError:
            pass
        started = time.monotonic()
        try:
            files = self.vcs().dirty_files()
        except Exception:  # noqa: BLE001
            return None
        if time.monotonic() - started > SLOW_SNAPSHOT_SECONDS:
            try:
                slow.parent.mkdir(parents=True, exist_ok=True)
                slow.write_text(f"{time.monotonic() - started:.1f}s", encoding="utf-8")
            except OSError:
                pass
            self.log("snapshot_slow", seconds=round(time.monotonic() - started, 1))
            if paused_ok:
                # 执行前就慢：放弃这次比对，免得执行后再等一遍
                return None
        if files is None:
            return None
        snapshot = {}
        for rel in files:
            try:
                stat = (self.root / rel).stat()
                snapshot[rel] = [stat.st_mtime_ns, stat.st_size]
            except OSError:
                snapshot[rel] = [0, -1]
        return snapshot

    def _pending_snapshots(self) -> dict:
        # 旧版状态文件里是单个快照或 None
        pending = self.state.data.get("shell_before")
        return pending if isinstance(pending, dict) and all(k.startswith("cmd:") for k in pending) else {}

    def _snapshot_before_shell(self, command: str) -> None:
        """按命令分开存快照：Cursor 并行执行的几条命令各自比对，不互相覆盖。"""
        if self.state is None or self.config.get("gate.mode") == "off" or self.state.data["skip"]:
            return
        snapshot = self._dirty_snapshot()
        if snapshot is not None:
            pending = self._pending_snapshots()
            pending[command_key(command)] = snapshot
            self.state.data["shell_before"] = dict(list(pending.items())[-MAX_PENDING_SNAPSHOTS:])
            self.save()

    def _only_committed(self, rel: str, before: dict, after: dict) -> bool:
        """git commit / svn commit 让文件不再“未提交”，但文件本身没动，不算命令改过。"""
        if rel in after:
            return False
        try:
            stat = (self.root / rel).stat()
        except OSError:
            return False
        return before.get(rel) == [stat.st_mtime_ns, stat.st_size]

    def _shell_after(self) -> dict:
        """命令实际改过的文件记为已编辑（结束时提醒写记忆）；改到没查过记忆的模块时立即提醒 Agent 补查。"""
        if self.state is None:
            return {}
        pending = self._pending_snapshots()
        command = str(tool_input(self.payload).get("command") or "")
        key = command_key(command)
        if key not in pending and len(pending) == 1 and needs_snapshot(command, str(self.root)):
            # 前后两次拿到的命令文本可能因转码不同；只有一条在等、且这条命令本身也会存快照时就是它。
            # 并行的 ls 这类命令先结束时不能把别的命令的快照拿走
            key = next(iter(pending))
        before = pending.pop(key, None)
        if before is None:
            return {}
        self.state.data["shell_before"] = pending
        after = self._dirty_snapshot(paused_ok=False)
        if after is None:
            self.save()
            return {}
        changed = sorted(rel for rel in set(before) | set(after)
                         if before.get(rel) != after.get(rel) and not self._only_committed(rel, before, after))
        # 编辑工具改过的文件已经过闸门检查；与终端命令并行改的不算到命令头上
        by_tools = {item.split("|", 1)[1] for item in self.state.data["edited_files"]}
        late: dict[str, list[str]] = {}
        for rel in changed:
            if not self._watched(rel) or rel in by_tools:
                continue
            self._mark_edited(rel)
            module = self.module_of(rel)
            if (module and not self.state.has("searched", module) and not self.state.has("late_warned", module)
                    and self.memory_count(module)):
                late.setdefault(module, []).append(rel)
        for module in late:
            self.state.add("late_warned", module)
        self.save()
        if not late:
            return {}
        messages = []
        for module, files in late.items():
            self.log("late_gate", module=module, files=files[:5])
            messages.append(
                f"[pmem] 刚才的终端命令改了 {'、'.join(files[:5])}，属于 {module}（已有 {self.memory_count(module)} 条研发记忆），"
                f"但本对话还没查过该模块的记忆。请立即调用 search_memory(module=\"{module}\") 核对这次修改，"
                "与记忆冲突就改回。" + self._pitfalls(module)[0]
            )
        return {"additional_context": "\n\n".join(messages)}
