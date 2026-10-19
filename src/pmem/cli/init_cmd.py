from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from pmem.generate.integrations import NEXT_STEPS, SETUP, pick_agents, write_text
from pmem.generate.templates import CATEGORY_PRESETS, CONFIG_TEMPLATE, MODULES_HEADER


def guess_type(root: Path) -> str:
    if (root / "Assets").is_dir() and (root / "ProjectSettings").is_dir():
        return "game"
    if any((root / f).exists() for f in ("go.mod", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml")):
        return "backend"
    if (root / "package.json").exists():
        return "app"
    return "generic"


def run_init(root: Path, project_type: str | None, gate: str | None = None, agents: str = "auto") -> int:
    root = root.resolve()
    memory = root / ".memory"
    config_path = memory / "config.yaml"
    modules_path = memory / "modules.yaml"
    # 重复运行不覆盖已有配置；显式给了 --gate / --type 却没生效时要说出来，否则用户以为改成了
    ignored = []
    if gate and config_path.exists():
        ignored.append(f"--gate {gate}：config.yaml 已存在，请直接改其中的 gate.mode")
    if project_type and config_path.exists() and modules_path.exists():
        ignored.append(f"--type {project_type}：config.yaml 和 modules.yaml 已存在，请直接改 project.type 与 categories")
    gate = gate or "block"
    project_type = project_type or guess_type(root)
    chosen = pick_agents(root, agents)
    done: list[str] = []

    if not config_path.exists():
        write_text(config_path, CONFIG_TEMPLATE.format(name=root.name, type=project_type, gate=gate))
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
        write_text(modules_path, text)
        done.append(f"创建 {modules_path.relative_to(root)}（大类：{' / '.join(CATEGORY_PRESETS[project_type])}）")
    (memory / "entries").mkdir(exist_ok=True)
    done += [SETUP[agent](root) for agent in chosen]

    print("pmem 接入完成：")
    for line in done:
        print(f"  - {line}")
    if ignored:
        print("\n以下参数没有生效（重复运行不覆盖已有配置）：")
        for line in ignored:
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
