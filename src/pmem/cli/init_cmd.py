from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml

from pmem.generate.templates import (
    BLOCK_BEGIN,
    BLOCK_END,
    BOOTSTRAP_SKILL,
    CATEGORY_PRESETS,
    CLAUDE_HOOKS,
    CODEX_HOOKS,
    CODEX_MCP_TOML,
    COMPACT_SKILL,
    CONFIG_TEMPLATE,
    GENERATED,
    HOOK_EVENTS,
    MCP_SERVER,
    MODULES_HEADER,
    NORMALIZE_SKILL,
    PLAIN_MCP_SERVER,
    RULE,
    RULE_BLOCK,
)

SUPPORTED_AGENTS = ("cursor", "claude", "codex")


def guess_type(root: Path) -> str:
    if (root / "Assets").is_dir() and (root / "ProjectSettings").is_dir():
        return "game"
    if any((root / f).exists() for f in ("go.mod", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml")):
        return "backend"
    if (root / "package.json").exists():
        return "app"
    return "generic"


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
    if unknown:
        raise SystemExit(f"不支持的 Agent：{'、'.join(unknown)}；可选 {', '.join(SUPPORTED_AGENTS)}、all、auto")
    return agents


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
    return str(command or "").startswith("pmem hook")


def merge_hooks(path: Path) -> None:
    data = _read_json(path)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    for event, entry in HOOK_EVENTS.items():
        kept = [h for h in hooks.get(event, []) if not _is_pmem(h.get("command"))]
        hooks[event] = [*kept, dict(entry)]
    _write_json(path, data)


def merge_group_hooks(path: Path, wanted: dict) -> None:
    """Claude Code / Codex 的三层结构（事件 → 匹配组 → 处理器）：去掉旧的 pmem 处理器后追加新的。"""
    data = _read_json(path)
    hooks = data.setdefault("hooks", {})
    for event, groups in wanted.items():
        kept = []
        for group in hooks.get(event, []):
            handlers = [h for h in group.get("hooks", []) if not _is_pmem(h.get("command"))]
            if handlers:
                kept.append({**group, "hooks": handlers})
        hooks[event] = [*kept, *json.loads(json.dumps(groups))]
    _write_json(path, data)


def merge_mcp(path: Path, server: dict = MCP_SERVER) -> None:
    data = _read_json(path)
    data.setdefault("mcpServers", {})["pmem"] = dict(server)
    _write_json(path, data)


def merge_codex_mcp(path: Path) -> bool:
    """在 .codex/config.toml 里登记 pmem；已有 [mcp_servers.pmem] 时不改。返回是否写入。"""
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if re.search(r'^\s*\[\s*mcp_servers\s*\.\s*"?pmem"?\s*\]', text, re.MULTILINE):
        return False
    separator = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    _write_text(path, text + separator + CODEX_MCP_TOML)
    return True


def upsert_block(path: Path, block: str) -> None:
    """在 CLAUDE.md / AGENTS.md 里写入或替换 pmem 段落，段落之外的内容保持不变。"""
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    start, end = text.find(BLOCK_BEGIN), text.find(BLOCK_END)
    if start >= 0 and end > start:
        tail = text[end + len(BLOCK_END):].lstrip("\n")
        text = text[:start] + block + ("\n" + tail if tail else "")
    else:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    _write_text(path, text)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_skills(folder: Path) -> None:
    for name, body in (("pmem-bootstrap", BOOTSTRAP_SKILL), ("pmem-compact", COMPACT_SKILL),
                       ("pmem-normalize", NORMALIZE_SKILL)):
        _write_text(folder / name / "SKILL.md", body.format(generated=GENERATED))


def setup_cursor(root: Path) -> str:
    cursor = root / ".cursor"
    _write_text(cursor / "rules" / "pmem.mdc", RULE.format(generated=GENERATED))
    _write_skills(cursor / "skills")
    merge_hooks(cursor / "hooks.json")
    merge_mcp(cursor / "mcp.json")
    return "Cursor：.cursor/rules/pmem.mdc、.cursor/skills/pmem-*、合并 .cursor/hooks.json 与 .cursor/mcp.json"


def setup_claude(root: Path) -> str:
    upsert_block(root / "CLAUDE.md", RULE_BLOCK)
    _write_skills(root / ".claude" / "skills")
    merge_group_hooks(root / ".claude" / "settings.json", CLAUDE_HOOKS)
    merge_mcp(root / ".mcp.json", PLAIN_MCP_SERVER)
    return "Claude Code：CLAUDE.md 中的 pmem 段落、.claude/skills/pmem-*、合并 .claude/settings.json 与 .mcp.json"


def setup_codex(root: Path) -> str:
    upsert_block(root / "AGENTS.md", RULE_BLOCK)
    merge_group_hooks(root / ".codex" / "hooks.json", CODEX_HOOKS)
    merge_codex_mcp(root / ".codex" / "config.toml")
    return "Codex：AGENTS.md 中的 pmem 段落、合并 .codex/hooks.json 与 .codex/config.toml"


SETUP = {"cursor": setup_cursor, "claude": setup_claude, "codex": setup_codex}
NEXT_STEPS = {
    "cursor": "Cursor：在设置 → MCP 中启用 pmem（首次需要点一次）。",
    "claude": "Claude Code：首次打开项目时批准 .mcp.json 里的 pmem 服务；/hooks 可查看已接入的 Hook。",
    "codex": "Codex：信任本项目后，在 /hooks 里审阅并信任 pmem 的 Hook（项目 .codex/ 未被信任时不加载）。",
}


def run_init(root: Path, project_type: str | None, gate: str, agents: str = "auto") -> int:
    root = root.resolve()
    memory = root / ".memory"
    project_type = project_type or guess_type(root)
    config_path = memory / "config.yaml"
    modules_path = memory / "modules.yaml"
    chosen = pick_agents(root, agents)
    done: list[str] = []

    if not config_path.exists():
        _write_text(config_path, CONFIG_TEMPLATE.format(name=root.name, type=project_type, gate=gate))
        done.append(f"创建 {config_path.relative_to(root)}（项目类型 {project_type}，闸门 {gate}）")
    if not modules_path.exists():
        body = {
            "schema_version": 1,
            "categories": {k: {"label": v} for k, v in CATEGORY_PRESETS[project_type].items()},
            "entities": {},
            "synonyms": [],
            "modules": {},
            "candidates": {},
            "third_party": [],
            "ignored": [],
        }
        text = MODULES_HEADER + yaml.safe_dump(body, allow_unicode=True, sort_keys=False)
        _write_text(modules_path, text)
        done.append(f"创建 {modules_path.relative_to(root)}（大类：{' / '.join(CATEGORY_PRESETS[project_type])}）")
    (memory / "entries").mkdir(exist_ok=True)
    done += [SETUP[agent](root) for agent in chosen]

    print("pmem 接入完成：")
    for line in done:
        print(f"  - {line}")
    if shutil.which("pmem") is None:
        print("\n注意：当前 PATH 中找不到 pmem 命令，Agent 将无法启动 MCP 与 Hooks。请先运行：uv tool install pmem")
    print("\n下一步：")
    for i, agent in enumerate(chosen, 1):
        print(f"  {i}. {NEXT_STEPS[agent]}")
    n = len(chosen)
    print(f"  {n + 1}. 对 Agent 说：“按 pmem-bootstrap 技能划分模块”。")
    print(f"  {n + 2}. 运行 pmem doctor 确认覆盖率，然后把 .memory/ 与上面生成的配置提交到版本库。")
    return 0
