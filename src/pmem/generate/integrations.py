"""各家 Agent 的接入文件：规则、技能、Hook、MCP 配置。合并时只替换 pmem 自己的条目，其他工具的配置原样保留。"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from pmem.core.winproc import no_window_kwargs
from pmem.generate.mcp_enable import enable_project_mcp
from pmem.generate.templates import (
    BLOCK_BEGIN,
    BLOCK_END,
    BOOTSTRAP_SKILL,
    CODEX_MCP_TOML,
    COMPACT_SKILL,
    CONSOLIDATE_SKILL,
    CURSOR_HOOKS,
    GENERATED,
    HOOK_WRAPPER,
    HOOK_WRAPPER_CMD,
    HOOK_WRAPPER_SH,
    MCP_SERVER,
    NORMALIZE_SKILL,
    PLAIN_MCP_SERVER,
    RULE,
    RULE_BLOCK,
    SEED_SKILL,
    SPEC_SKILL,
    claude_hooks,
    codex_hooks,
    cursor_hooks,
)

SUPPORTED_AGENTS = ("cursor", "claude", "codex")


def pick_agents(root: Path, raw: str) -> list[str]:
    raw = (raw or "auto").strip().lower()
    if raw == "all":
        return list(SUPPORTED_AGENTS)
    if raw == "auto":
        agents = ["cursor"]
        if (root / ".claude").is_dir() or (root / "CLAUDE.md").exists():
            agents.append("claude")
        if (root / ".codex").is_dir() or (root / "AGENTS.md").exists():
            agents.append("codex")
        return agents
    agents = [a.strip() for a in raw.split(",") if a.strip()]
    unknown = [a for a in agents if a not in SUPPORTED_AGENTS]
    if not agents:
        raise SystemExit(f"--agents 没有给出 Agent；可选 {', '.join(SUPPORTED_AGENTS)}、all、auto")
    if unknown:
        raise SystemExit(f"不支持的 Agent：{'、'.join(unknown)}；可选 {', '.join(SUPPORTED_AGENTS)}、all、auto")
    return agents


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} 不是合法 JSON，请先修复：{exc}") from exc
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _is_pmem(command) -> bool:
    text = str(command or "")
    return text.startswith(("pmem hook", "pmemw hook", HOOK_WRAPPER))


def _is_pmem_handler(handler) -> bool:
    return isinstance(handler, dict) and _is_pmem(handler.get("command"))


def _hook_table(data: dict, path: Path) -> dict:
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict) or not all(isinstance(v, list) for v in hooks.values()):
        raise SystemExit(f"{path} 的 hooks 应为“事件名 → 列表”，当前结构不对，请先修复")
    return hooks


def write_hook_wrappers(root: Path) -> None:
    """.memory/bin/pmem-hook（macOS/Linux）与 pmem-hook.cmd（Windows，PowerShell 会优先选它）。"""
    folder = root / ".memory" / "bin"
    write_text(folder / "pmem-hook", HOOK_WRAPPER_SH)
    (folder / "pmem-hook.cmd").write_text(HOOK_WRAPPER_CMD, encoding="ascii", newline="\r\n")
    # 批处理用 LF 换行时 goto 标签可能失效，不能让 Git 按平台改换行
    write_text(folder / ".gitattributes", "*.cmd text eol=crlf\npmem-hook text eol=lf\n")
    script = folder / "pmem-hook"
    script.chmod(script.stat().st_mode | 0o755)
    # Windows 上建的文件没有可执行位，提交后 macOS/Linux 的队友无法运行；Git 下直接在暂存区里标上（不是 Git 仓库时无效果）
    if shutil.which("git"):
        # Windows 下 git 是 CUI；走 core.winproc，不能 import vcs（层级）。
        subprocess.run(
            ["git", "add", "--chmod=+x", "--", str(script)],
            cwd=root,
            capture_output=True,
            check=False,
            **no_window_kwargs(),
        )


def merge_hooks(path: Path, wanted: dict | None = None) -> None:
    wanted = wanted or CURSOR_HOOKS
    data = _read_json(path)
    data.setdefault("version", 1)
    hooks = _hook_table(data, path)
    for event in list(hooks):
        if event not in wanted:
            kept = [h for h in hooks[event] if not _is_pmem_handler(h)]
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    for event, entry in wanted.items():
        kept = [h for h in hooks.get(event, []) if not _is_pmem_handler(h)]
        hooks[event] = [*kept, dict(entry)]
    _write_json(path, data)


def merge_group_hooks(path: Path, wanted: dict) -> None:
    """Claude Code / Codex 的三层结构（事件 → 匹配组 → 处理器）：去掉旧的 pmem 处理器后追加新的；
    模板里已经没有的事件下的 pmem 处理器同样删掉。"""
    data = _read_json(path)
    hooks = _hook_table(data, path)

    def without_pmem(groups: list) -> list:
        kept = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept.append(group)
                continue
            handlers = [h for h in group["hooks"] if not _is_pmem_handler(h)]
            if handlers:
                kept.append({**group, "hooks": handlers})
        return kept

    for event in list(hooks):
        if event not in wanted:
            kept = without_pmem(hooks[event])
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    for event, groups in wanted.items():
        hooks[event] = [*without_pmem(hooks.get(event, [])), *json.loads(json.dumps(groups))]
    _write_json(path, data)


def merge_mcp(path: Path, server: dict = MCP_SERVER) -> None:
    data = _read_json(path)
    data.setdefault("mcpServers", {})["pmem"] = dict(server)
    _write_json(path, data)


def merge_codex_mcp(path: Path) -> bool:
    """在 .codex/config.toml 里登记 pmem；已有段若误用 pmemw 则改回 pmem（MCP stdio）。返回是否写入。"""
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if re.search(r'^\s*\[\s*mcp_servers\s*\.\s*"?pmem"?\s*\]', text, re.MULTILINE):
        updated = re.sub(
            r'(?m)^(\s*\[\s*mcp_servers\s*\.\s*"?pmem"?\s*\][^\[]*?^\s*command\s*=\s*)"pmemw"',
            r'\1"pmem"',
            text,
            count=1,
        )
        if updated != text:
            write_text(path, updated)
            return True
        return False
    separator = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    write_text(path, text + separator + CODEX_MCP_TOML)
    return True


def upsert_block(path: Path, block: str) -> None:
    """在 CLAUDE.md / AGENTS.md 里写入或替换 pmem 段落，段落之外的内容保持不变。"""
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    start = text.find(BLOCK_BEGIN)
    end = text.find(BLOCK_END, start) if start >= 0 else -1
    if start >= 0 and end > start:
        tail = text[end + len(BLOCK_END):].lstrip("\n")
        text = text[:start] + block + ("\n" + tail if tail else "")
    else:
        # 结束标记被删掉时不知道旧段落到哪为止：只去掉孤立的开始标记，免得下次把中间的用户内容当段落替换掉
        text = text.replace(BLOCK_BEGIN, "")
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    write_text(path, text)


def _write_skills(folder: Path) -> None:
    for name, body in (("pmem-bootstrap", BOOTSTRAP_SKILL), ("pmem-compact", COMPACT_SKILL),
                       ("pmem-consolidate", CONSOLIDATE_SKILL), ("pmem-normalize", NORMALIZE_SKILL),
                       ("pmem-seed", SEED_SKILL), ("pmem-spec", SPEC_SKILL)):
        write_text(folder / name / "SKILL.md", body.format(generated=GENERATED))


def setup_cursor(root: Path, hooks_mode: str = "auto") -> str:
    cursor = root / ".cursor"
    write_text(cursor / "rules" / "pmem.mdc", RULE.format(generated=GENERATED))
    _write_skills(cursor / "skills")
    wanted = cursor_hooks(hooks_mode)
    merge_hooks(cursor / "hooks.json", wanted)
    merge_mcp(cursor / "mcp.json")
    write_hook_wrappers(root)
    enabled = enable_project_mcp("cursor", root)
    post_matcher = str((wanted.get("postToolUse") or {}).get("matcher") or "")
    if not wanted:
        mode = "off"
    elif "afterFileEdit" in wanted or "preCompact" in wanted or re.search(
        r"Read|Grep|Glob|SemanticSearch|codebase_search", post_matcher
    ):
        mode = "full"
    else:
        mode = "quiet"
    return ("Cursor：.cursor/rules/pmem.mdc、.cursor/skills/pmem-*、合并 .cursor/hooks.json 与 .cursor/mcp.json、"
            f".memory/bin/pmem-hook*（没装 pmem 时提醒）；Hooks={mode}"
            + ("（闸门保留；postToolUse 仅 Shell，无读码摘要）"
               if mode == "quiet" else ("（已去掉全部 pmem Hook）" if mode == "off"
                                        else "（完整闸门+读码摘要+提醒；Hook=pmemw）"))
            + f"；{enabled}")


def setup_claude(root: Path, hooks_mode: str = "auto", *, paired_with_cursor: bool = False) -> str:
    upsert_block(root / "CLAUDE.md", RULE_BLOCK)
    _write_skills(root / ".claude" / "skills")
    wanted = claude_hooks(hooks_mode, paired_with_cursor=paired_with_cursor)
    merge_group_hooks(root / ".claude" / "settings.json", wanted)
    merge_mcp(root / ".mcp.json", PLAIN_MCP_SERVER)
    enabled = enable_project_mcp("claude", root)
    if not wanted:
        extra = "；Hooks 已清空（与 Cursor 同开时避免双开翻倍弹窗）"
    elif "Read" not in str((wanted.get("PostToolUse") or [{}])[0].get("matcher", "")):
        extra = "；Hooks=quiet（PostToolUse 无 Read|Grep）"
    else:
        extra = ""
    return ("Claude Code：CLAUDE.md 中的 pmem 段落、.claude/skills/pmem-*、合并 .claude/settings.json 与 .mcp.json"
            + extra + f"；{enabled}")

def setup_codex(root: Path, hooks_mode: str = "auto") -> str:
    upsert_block(root / "AGENTS.md", RULE_BLOCK)
    # Codex 只从 .agents/skills 读项目技能
    _write_skills(root / ".agents" / "skills")
    wanted = codex_hooks(hooks_mode)
    merge_group_hooks(root / ".codex" / "hooks.json", wanted)
    merge_codex_mcp(root / ".codex" / "config.toml")
    enabled = enable_project_mcp("codex", root)
    if not wanted:
        extra = "；Hooks 已清空"
    elif "PreCompact" not in wanted and "UserPromptSubmit" in wanted:
        extra = "；Hooks=quiet（闸门+prompt/stop 保留，无 PreCompact）"
    else:
        extra = ""
    return ("Codex：AGENTS.md 中的 pmem 段落、.agents/skills/pmem-*、合并 .codex/hooks.json 与 .codex/config.toml"
            + extra + f"；{enabled}")


SETUP = {"cursor": setup_cursor, "claude": setup_claude, "codex": setup_codex}
NEXT_STEPS = {
    "cursor": "Cursor：init 已尝试项目级批准 pmem；若 MCP 仍显示 Disconnected，执行 Reload Window。不要改用户级 ~/.cursor/mcp.json。",
    "claude": "Claude Code：init 已尝试把项目 .mcp.json 的 pmem 写入 enabledMcpjsonServers；/hooks 可查看 Hook。",
    "codex": "Codex：init 已尝试把本项目标为 trusted 以加载 .codex/ 的 pmem；Hook 若仍提示未信任，在 /hooks 里点一次信任。",
}
