from __future__ import annotations

import time
from pathlib import Path

from pmem.core import autosync, seen
from pmem.core.codefiles import is_code_file
from pmem.core.config import Config
from pmem.core.entry import Entry
from pmem.core.registry import ModuleRegistry
from pmem.hooks.guard import Guard
from pmem.hooks.mcp import ALLOW, PMEM_TOOLS, McpCalls, foreign_tool
from pmem.hooks.memories import MemoryView
from pmem.hooks.payload import asks_to_skip, fuzzy_contains, readable, tool_input
from pmem.hooks.reminders import Reminders
from pmem.hooks.review import MAX_REVIEW_MODULES, SEARCH_TOOLS, Review
from pmem.hooks.shell import (  # noqa: F401
    cli_args,
    may_change_unseen,
    scan,
    searched_before_writes,
    shell_write_targets,
)
from pmem.hooks.snapshot import Snapshots, needs_snapshot
from pmem.hooks.state import SessionState

WRITE_TOOLS = {"write", "strreplace", "edit", "multiedit", "editnotebook", "delete", "search_replace"}
ERROR_LOG = "hook-errors.log"
ERROR_SEEN = "hook-errors.seen"
ERROR_NOTICE_WINDOW = 24 * 3600


def _around(text: str, marker: str, width: int = 12) -> str:
    """提问里触发标记的那一小段，方便看出是不是误判。"""
    flat = " ".join(text.split())
    at = flat.find(marker)
    if at < 0:
        return flat[: width * 2 + len(marker)]
    start, end = max(0, at - width), at + len(marker) + width
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


class Gate(MemoryView, Review, Guard, McpCalls, Snapshots, Reminders):
    """各类 Hook 事件的入口；具体逻辑按职责分在各个基类里，共用会话状态和配置。"""

    def __init__(self, root: Path, payload: dict):
        self.root = root
        self.payload = payload
        self.config = Config.load(root)
        self.conversation = str(payload.get("conversation_id") or "")
        self.state = SessionState(self.config.cache_dir, self.conversation) if self.conversation else None
        modules_path = self.config.modules_path
        self.registry = ModuleRegistry.load(modules_path) if modules_path.exists() else ModuleRegistry({})
        self._files: dict[str, Path] = {}
        self._entries: dict[str, list[Entry]] = {}
        # 持有会话锁时只留占位符，释放后由 fill_stale 统一核对，免得并发的 Hook 排队等版本库查询
        self.defer_stale = False
        self._deferred: dict[str, Entry] = {}

    # 事件

    def on_prompt(self) -> dict:
        text = str(self.payload.get("prompt") or "")
        markers = self.config.get("gate.skip_markers") or []
        skip_marker = next((str(m) for m in markers if asks_to_skip(text, str(m))), None)
        skip = skip_marker is not None
        resume = any(asks_to_skip(text, str(m)) for m in self.config.get("gate.resume_markers") or [])
        analysis = any(
            fuzzy_contains(text.lower() if m.isascii() else text, m.lower() if m.isascii() else m)
            for m in (str(m) for m in self.config.get("gate.analysis_markers") or [])
        )
        asked = self.modules_in_text(text) if self.state is not None else []
        if self.state is not None:
            if resume:
                self.state.data.update(skip=False, skip_reason="", skip_noticed=False)
            elif skip and not self.state.data["skip"]:
                self.state.data.update(skip=True, skip_reason=_around(readable(text, skip_marker), skip_marker))
            self.state.data["analysis"] = self.state.data["analysis"] or analysis
            self.state.data["asked"] = asked
            self.save()
        self.log("prompt", mode=self.payload.get("composer_mode"), skip=skip or None, resume=resume or None,
                 analysis=analysis or None, asked=asked or None)
        result: dict = {"continue": True}
        # 只有能在提问时注入上下文的工具（Claude Code）才当场附上摘要；Cursor 靠读代码时的摘要和回合结束的核对
        if self.payload.get("prompt_context") and self._reviews_on("gate.question_review"):
            digests = [d for d in (self._offer_digest(m, f"你的问题提到了 {m}") for m in asked[:MAX_REVIEW_MODULES]) if d]
            if digests:
                result["additional_context"] = "\n\n".join(digests)
        return result


    def on_pre_tool(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        args = tool_input(self.payload)
        if any(t in name for t in PMEM_TOOLS) and foreign_tool(self.payload):
            return dict(ALLOW)
        if "record_memory" in name:
            return self._inject(args, with_draft=True)
        # MCP 检索在返回结果之后（after-mcp / post-tool）才登记为查过，调用失败不算
        if "search_memory" in name:
            # Cursor 的 tool_name 不带服务名，别家记忆服务的同名工具可能拒收多出的参数
            if "pmem" in name.lower() or self.module_from_args(args):
                return self._inject(args, with_draft=False)
            return dict(ALLOW)
        if "memory_graph" in name:
            return dict(ALLOW)
        if name.lower() == "shell":
            command = str(args.get("command") or "")
            # 命令里的 pmem search 先挂起，执行完才算查过；同一条命令里，按顺序接在某模块检索之后的写入先放行
            # （检索失败时执行后补提醒，见 _confirm_cli_calls），先写后查、隔着 || 或 & 的照样检查
            in_command = self._note_cli_calls(command)
            base = args.get("cwd") or str(self.root)
            targets, _ = scan(command, base)
            before = searched_before_writes(command, base) if in_command else {}

            def searched_first(target: str) -> set[str]:
                return {m for m in map(self.module_from_args, before.get(target, [])) if m}

            denied = next((v for v in (self._guard(self.relative(t, base), searched_first(t)) for t in targets)
                           if v is not None), None)
            if denied is not None:
                return denied
            if needs_snapshot(command, base):
                self._snapshot_before_shell(command)
            return dict(ALLOW)
        if name.lower() not in WRITE_TOOLS:
            return dict(ALLOW)
        raw = args.get("file_paths") or [args.get("file_path") or args.get("path") or args.get("target_file")
                                         or args.get("target_notebook") or ""]
        guarded = (self._guard_path(self.relative(str(p)), frozenset()) for p in raw)
        return next((v for v in guarded if v is not None), dict(ALLOW))


    def on_edited(self) -> dict:
        self._mark_edited(str(self.payload.get("file_path") or ""))
        return {}

    def _mark_edited(self, path: str) -> None:
        rel = self.relative(path)
        module = self.module_of(rel)
        if module and self.state is not None:
            self.state.add("edited", module)
            self.state.add("edited_files", f"{module}|{rel}")
            self.save()
        if rel is not None:
            self.log("edit", module=module, file=rel)
            if module is None and self._unregistered_code(rel):
                self._autosync("edit")

    def _unregistered_code(self, rel: str) -> bool:
        """改到的是没归属任何模块的代码文件（不算第三方、忽略的目录和闸门不看的文件）。"""
        if not is_code_file(rel) or not self._watched(rel) or self.registry.is_excluded(rel):
            return False
        try:
            return self.registry.module_for_path(rel) is None
        except Exception:  # noqa: BLE001
            return False

    def _autosync(self, reason: str) -> None:
        if autosync.should_spawn(self.config, reason):
            started = autosync.spawn(self.root, self.config.cache_dir, reason)
            self.log("autosync_spawn", reason=reason, ok=started)

    def on_session(self) -> dict:
        self._autosync("session")
        return {}

    def on_post_tool(self) -> dict:
        result = self._post_tool()
        notices = [self.error_notice()]
        if self.config.get("sync.auto") != "off":
            notices.append(autosync.take_notice(self.config.cache_dir))
        if any(notices):
            result = dict(result or {})
            result["additional_context"] = "\n\n".join(filter(None, [result.get("additional_context"), *notices]))
        return result

    def error_notice(self) -> str | None:
        """Hook 出错时默认放行（不能卡住开发），但用户得知道闸门那次没起作用：有新错误就提醒一次。"""
        if self.config.get("gate.mode") == "off":
            return None
        log = self.config.cache_dir / ERROR_LOG
        seen = self.config.cache_dir / ERROR_SEEN
        try:
            changed = log.stat().st_mtime
        except OSError:
            return None
        try:
            last_seen = seen.stat().st_mtime
        except OSError:
            last_seen = time.time() - ERROR_NOTICE_WINDOW
        if changed <= last_seen:
            return None
        try:
            seen.parent.mkdir(parents=True, exist_ok=True)
            seen.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
            tail = log.read_bytes()[-4096:].decode("utf-8", "replace")
        except OSError:
            return None
        lines = [line.strip() for line in tail.splitlines() if line.strip()]
        last = lines[-1][:200] if lines else ""
        self.log("error_notice", error=last)
        return (f"[pmem] 记忆闸门刚才出错，那次已自动放行、没有做记忆检查（{last}）。"
                f"请在回复里提醒用户运行 pmem doctor 查看原因（错误日志：{log}）。")

    def _post_tool(self) -> dict:
        """工具调用之后：读代码时附上该模块的记忆摘要；Claude Code / Codex 另由此处理 pmem 工具的返回与编辑过的文件。"""
        from pmem.hooks.agents import edited_files

        name = str(self.payload.get("tool_name") or "")
        if any(t in name for t in PMEM_TOOLS):
            return self.on_after_mcp()
        if name.lower() == "read":
            return self._read_digest(tool_input(self.payload))
        if name.lower() in SEARCH_TOOLS:
            return self._search_digest(tool_input(self.payload))
        if name.lower() == "shell":
            failed = self._confirm_cli_calls()
            result = self._shell_after()
            if failed:
                result = dict(result or {})
                result["additional_context"] = "\n\n".join(filter(None, [result.get("additional_context"), failed]))
            return result
        for path in edited_files(self.payload):
            self._mark_edited(path)
        return {}


    def on_compact(self) -> dict:
        if self.state is not None:
            # 压缩后之前看过的记忆可能已不在上下文里：检索也要重新给全文
            for key in ("searched", "warned", "reviewed", "project_shown"):
                self.state.data[key] = []
            self.state.data["project_done"] = False
            self.state.data["stale_explained"] = False
            self.save()
            seen.clear(self.config.cache_dir, self.conversation)
        self.log("compact", trigger=self.payload.get("trigger"))
        return {}


HANDLERS = {
    # 新对话开始：按间隔在后台扫描没登记的代码目录；没装 pmem 时由 .memory/bin/pmem-hook 包装脚本提醒
    "session": Gate.on_session,
    "prompt": Gate.on_prompt,
    "pre-tool": Gate.on_pre_tool,
    "before-mcp": Gate.on_before_mcp,
    "after-mcp": Gate.on_after_mcp,
    "edited": Gate.on_edited,
    "post-tool": Gate.on_post_tool,
    "compact": Gate.on_compact,
    "stop": Gate.on_stop,
}


def handle(event: str, payload: dict, root: Path) -> dict:
    handler = HANDLERS.get(event)
    if handler is None:
        return {}
    gate = Gate(Path(root), payload)
    if gate.state is None:
        return handler(gate)
    gate.defer_stale = True
    with gate.state.locked():
        result = handler(gate)
    gate.defer_stale = False
    return gate.fill_stale(result)
