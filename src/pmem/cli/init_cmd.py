from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from pmem.generate.templates import (
    BOOTSTRAP_SKILL,
    CATEGORY_PRESETS,
    CONFIG_TEMPLATE,
    GENERATED,
    HOOK_EVENTS,
    MCP_SERVER,
    MODULES_HEADER,
    RULE,
)


def guess_type(root: Path) -> str:
    if (root / "Assets").is_dir() and (root / "ProjectSettings").is_dir():
        return "game"
    if any((root / f).exists() for f in ("go.mod", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml")):
        return "backend"
    if (root / "package.json").exists():
        return "app"
    return "generic"


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


def merge_hooks(path: Path) -> None:
    data = _read_json(path)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    for event, entry in HOOK_EVENTS.items():
        kept = [h for h in hooks.get(event, []) if not str(h.get("command", "")).startswith("pmem hook")]
        hooks[event] = [*kept, dict(entry)]
    _write_json(path, data)


def merge_mcp(path: Path) -> None:
    data = _read_json(path)
    data.setdefault("mcpServers", {})["pmem"] = dict(MCP_SERVER)
    _write_json(path, data)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def run_init(root: Path, project_type: str | None, gate: str) -> int:
    root = root.resolve()
    memory = root / ".memory"
    project_type = project_type or guess_type(root)
    config_path = memory / "config.yaml"
    modules_path = memory / "modules.yaml"
    done: list[str] = []

    if not config_path.exists():
        _write_text(config_path, CONFIG_TEMPLATE.format(name=root.name, type=project_type, gate=gate))
        done.append(f"创建 {config_path.relative_to(root)}（项目类型 {project_type}，闸门 {gate}）")
    if not modules_path.exists():
        body = {
            "schema_version": 1,
            "categories": {k: {"label": v} for k, v in CATEGORY_PRESETS[project_type].items()},
            "entities": {},
            "modules": {},
            "candidates": {},
            "third_party": [],
            "ignored": [],
        }
        text = MODULES_HEADER + yaml.safe_dump(body, allow_unicode=True, sort_keys=False)
        _write_text(modules_path, text)
        done.append(f"创建 {modules_path.relative_to(root)}（大类：{' / '.join(CATEGORY_PRESETS[project_type])}）")
    (memory / "entries").mkdir(exist_ok=True)

    cursor = root / ".cursor"
    _write_text(cursor / "rules" / "pmem.mdc", RULE.format(generated=GENERATED))
    _write_text(cursor / "skills" / "pmem-bootstrap" / "SKILL.md", BOOTSTRAP_SKILL.format(generated=GENERATED))
    merge_hooks(cursor / "hooks.json")
    merge_mcp(cursor / "mcp.json")
    done.append("生成 .cursor/rules/pmem.mdc、.cursor/skills/pmem-bootstrap、合并 .cursor/hooks.json 与 .cursor/mcp.json")

    print("pmem 接入完成：")
    for line in done:
        print(f"  - {line}")
    if shutil.which("pmem") is None:
        print("\n注意：当前 PATH 中找不到 pmem 命令，Cursor 将无法启动 MCP 与 Hooks。请先运行：uv tool install pmem")
    print(
        "\n下一步：\n"
        "  1. 在 Cursor 设置 → MCP 中启用 pmem（首次需要点一次启用）。\n"
        "  2. 在 Cursor 里对 Agent 说：“按 pmem-bootstrap 技能划分模块”。\n"
        "  3. 运行 pmem doctor 确认覆盖率，然后把 .memory/ 与 .cursor/ 提交到版本库。"
    )
    return 0
