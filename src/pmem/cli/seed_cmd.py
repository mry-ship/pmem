"""pmem seed：种子记忆的候选模块、待确认列表、转正与退回（配合 pmem-seed 技能）。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pmem.core.registry import RegistryError
from pmem.scan.lite import HEAT_DAYS, file_heat
from pmem.service import MemoryService

ENOUGH_MEMORIES = 10


def seed_plan(service: MemoryService, top: int) -> dict:
    """按近半年改动热度排出值得先补种子记忆的模块；已有足够记忆的排在后面。"""
    registry = service.registry
    vcs, heat = file_heat(service.root)
    module_heat: Counter = Counter()
    for path, count in heat.items():
        try:
            match = registry.module_for_path(path)
        except RegistryError:
            continue
        if match is not None and not match.candidate:
            module_heat[match.module_id] += count
    current = Counter(e.module for e in service.index.visible())
    seeds = Counter(e.module for e in service.index.visible() if e.status == "seed")
    rows = [
        {"module": mid, "heat": module_heat[mid], "memories": current[mid], "seeds": seeds[mid],
         "paths": module.paths}
        for mid, module in registry.modules.items() if not module.merged_into
    ]
    rows.sort(key=lambda r: (r["memories"] >= ENOUGH_MEMORIES, -r["heat"], r["module"]))
    return {"ok": True, "vcs": vcs, "modules": rows[:top]}


def render_plan(plan: dict) -> str:
    if not plan["modules"]:
        return "modules.yaml 里还没有模块，先按 pmem-bootstrap 技能划分模块"
    lines = [f"种子记忆候选模块（热度 = 近 {HEAT_DAYS} 天改动该模块文件的次数；已有 {ENOUGH_MEMORIES} 条以上记忆的排在后面）："]
    for r in plan["modules"]:
        extra = f"，待确认种子 {r['seeds']} 条" if r["seeds"] else ""
        lines.append(f"  {r['module']}  热度 {r['heat']}  现行记忆 {r['memories']} 条{extra}  路径：{', '.join(r['paths'][:4])}")
    log = {"git": "git log --no-merges --date=short --format=\"%h %ad %s\" -n 80 -- <目录>",
           "svn": "svn log -l 80 <目录>"}.get(plan["vcs"], "（无版本库：只看文档与代码注释）")
    lines += [
        "",
        f"提交说明：{log}",
        "写入：pmem record --seed --module <模块> --entity <议题> --kind <类型> --content-file <文件> --anchor <路径#函数>",
        "写完：pmem seed 查看待确认列表；确认后 pmem seed --accept --module <模块>，不要的 pmem seed --reject <id>",
    ]
    return "\n".join(lines)


def render_seeds(result: dict) -> str:
    rows = result["seeds"]
    if not rows:
        return "没有待确认的种子记忆。按 pmem-seed 技能提炼，或运行 pmem seed --plan 查看候选模块"
    lines = [f"待确认的种子记忆 {len(rows)} 条："]
    module = None
    for r in rows:
        if r["module"] != module:
            module = r["module"]
            lines.append(f"  {module}（{sum(1 for x in rows if x['module'] == module)} 条）")
        lines.append(f"    [{r['id']}] {r['entity']} · {r['kind']}：{r['preview']}")
    lines += ["", "全部确认：pmem seed --accept --module <模块>（或 --all）；逐条：pmem seed --accept <id> ...",
              "退回不要的：pmem seed --reject <id> ...（标为归档，不再出现在检索里）"]
    return "\n".join(lines)


def run_seed(root: Path, ids: list[str], module: str, plan: bool, top: int, accept: bool, reject: bool,
             accept_all: bool, as_json: bool) -> int:
    service = MemoryService(root)
    try:
        if plan:
            result = seed_plan(service, top)
            text = render_plan(result) if result.get("ok") else ""
        elif accept or reject:
            if not ids:
                if reject or not (module or accept_all):
                    print("请给出记忆 id；整模块确认用 --module <模块>，全部确认用 --all")
                    return 2
                listed = service.seeds(module or None)
                if not listed.get("ok"):
                    print(json.dumps(listed, ensure_ascii=False, indent=2))
                    return 1
                ids = [r["id"] for r in listed["seeds"]]
            result = service.change_status(ids, "accept" if accept else "reject")
            done = "转为正式记忆" if accept else "退回（已归档）"
            text = f"已{done} {len(result['changed'])} 条"
            if result.get("skipped"):
                text += f"；跳过 {len(result['skipped'])} 条不是种子状态的记忆"
            if result.get("missing"):
                text += f"；找不到：{', '.join(result['missing'])}"
            if result["changed"]:
                text += "。记得提交 .memory/"
        else:
            result = service.seeds(module or None)
            text = render_seeds(result) if result.get("ok") else ""
    finally:
        service.close()
    if as_json or not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0 if result.get("ok") else 1
