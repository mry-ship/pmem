"""各家 Agent 的 Hook 输入输出与闸门（按 Cursor 的形状编写）之间的转换。

Claude Code 与 Codex 的 Hook 协议基本一致：输入带 session_id / tool_name / tool_input，
PreToolUse 用 hookSpecificOutput.permissionDecision 拦截，Stop 用 decision=block 让 Agent 继续，
UserPromptSubmit / PostToolUse 用 hookSpecificOutput.additionalContext 给模型补充上下文。
"""
from __future__ import annotations

import re
from pathlib import Path

AGENTS = ("cursor", "claude", "codex")

# 编辑类工具统一成闸门认识的名字；文件路径统一放进 file_paths
_EDIT_TOOLS = {"write": "Write", "edit": "Edit", "multiedit": "MultiEdit", "notebookedit": "EditNotebook"}
_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$|^\*\*\* Move to:\s*(.+?)\s*$", re.MULTILINE)


def patch_files(patch: str) -> list[str]:
    """Codex apply_patch 补丁里涉及的文件（新增、修改、删除、改名目标）。"""
    return [a or b for a, b in _PATCH_FILE.findall(patch or "")]


def _command(value) -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value or "")


def _absolute(path: str, cwd: str | None) -> str:
    if not path or Path(path).is_absolute() or not cwd:
        return path
    return str(Path(cwd) / path)


def normalize(agent: str, payload: dict) -> dict:
    """把 Claude Code / Codex 的输入转换成闸门使用的 Cursor 形状；Cursor 原样返回。"""
    if agent == "cursor":
        return payload
    data = dict(payload)
    data["conversation_id"] = payload.get("session_id") or payload.get("conversation_id") or ""
    # Claude Code、Codex 的 UserPromptSubmit 可以给这一轮加上下文；Cursor 的 beforeSubmitPrompt 不行
    data["prompt_context"] = True
    name = str(payload.get("tool_name") or "")
    args = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    cwd = payload.get("cwd")
    lowered = name.lower()
    # Claude Code 在 Windows 上另有 PowerShell 工具，和 Bash 一样按终端命令核对
    if lowered in ("bash", "powershell"):
        data["tool_name"] = "Shell"
        data["tool_input"] = {"command": _command(args.get("command")), "cwd": cwd}
    elif lowered == "apply_patch":
        files = [_absolute(p, cwd) for p in patch_files(_command(args.get("command") or args.get("input")))]
        data["tool_name"] = "Write"
        data["tool_input"] = {"file_paths": files}
    elif lowered in _EDIT_TOOLS:
        raw = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
        data["tool_name"] = _EDIT_TOOLS[lowered]
        data["tool_input"] = {"file_paths": [_absolute(str(raw), cwd)] if raw else []}
    return data


def edited_files(payload: dict) -> list[str]:
    """PostToolUse 里编辑类工具改过的文件（已是 normalize 之后的形状）。"""
    if str(payload.get("tool_name") or "").lower() not in {v.lower() for v in _EDIT_TOOLS.values()}:
        return []
    args = payload.get("tool_input") or {}
    return [str(p) for p in args.get("file_paths") or [] if p]


_EVENT_NAMES = {"pre-tool": "PreToolUse", "post-tool": "PostToolUse", "prompt": "UserPromptSubmit",
                "compact": "PreCompact", "stop": "Stop"}


def render(agent: str, event: str, result: dict) -> dict:
    """把闸门的结果转换成目标 Agent 认识的输出。"""
    if agent == "cursor" or not result:
        return result if agent == "cursor" else {}
    if event == "pre-tool":
        if result.get("permission") == "deny":
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": result.get("agent_message") or result.get("user_message") or "",
            }}
        # 只有 pmem 自己的 MCP 工具会带 updated_input；普通 allow 不能回传，否则会替用户批准 Bash 等调用
        if result.get("updated_input"):
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": result["updated_input"],
            }}
        return {}
    if event == "stop" and result.get("followup_message"):
        # Claude Code 2.1.163 起 Stop 才认 hookSpecificOutput.additionalContext，更早的版本直接忽略；
        # decision=block 各版本都认（界面上标为 hook 反馈），与 Codex 同一写法
        return {"decision": "block", "reason": result["followup_message"]}
    if event in ("prompt", "post-tool") and result.get("additional_context"):
        return {"hookSpecificOutput": {"hookEventName": _EVENT_NAMES[event],
                                       "additionalContext": result["additional_context"]}}
    return {}
