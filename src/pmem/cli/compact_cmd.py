"""pmem compact：找出积累了多条零碎记忆的议题，把正文交给 Agent 合并成一条。"""
from __future__ import annotations

import json
from pathlib import Path

from pmem.core.entry import KIND_LABELS
from pmem.service import MemoryService


def _kinds(kinds: dict) -> str:
    return "、".join(f"{KIND_LABELS.get(k, k)} {n}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))


def render_groups(result: dict) -> str:
    groups = result["groups"]
    if not groups:
        return f"没有积累到 {result['min_size']} 条以上记忆的议题，暂不需要合并。"
    lines = [f"可合并的议题 {len(groups)} 个（每个至少 {result['min_size']} 条，共 {result['memories']} 条记忆）："]
    for g in groups:
        lines.append(f"  {g['module']} / {g['entity']}：{g['count']} 条，{g['chars']} 字，"
                     f"{g['first']} ~ {g['last']}，{_kinds(g['kinds'])}")
    lines += ["", "查看某个议题的全部正文：pmem compact --module <模块> --entity <议题>"]
    return "\n".join(lines)


def render_group(result: dict) -> str:
    items = result["items"]
    lines = [f"{result['module']} / {result['entity']}：{len(items)} 条有效记忆，共 {result['chars']} 字（从旧到新）", ""]
    for item in items:
        lines.append(f"[{item['id']}] {item['date']} {KIND_LABELS.get(item['kind'], item['kind'])} {item['author']}")
        lines.append(item["content"])
        if item["anchors"]:
            lines.append("关联代码：" + "、".join(item["anchors"]))
        lines.append("")
    supersedes = " ".join(f"--supersedes {item['id']}" for item in items)
    lines += [
        "合并方法：把仍然成立的结论、排除项和风险提炼成一条（被后来推翻的只保留最终结论），写入 merged.md 后执行",
        (f"  pmem record --module {result['module']} --entity {result['entity']} --kind <类型> "
         f"--content-file merged.md {supersedes}"),
        "被替代的旧记忆不再出现在检索结果里，文件保留在版本库中可追溯；关联代码会自动继承。",
        "合并错了（丢了内容、并了不该并的）：pmem compact --undo <合并后的新记忆 id>，原记忆重新现行。",
    ]
    return "\n".join(lines)


def render_revert(result: dict) -> str:
    lines = [f"已撤销合并：{result['id']} 已归档，不再替代原记忆。"]
    if result["restored"]:
        lines.append(f"重新现行的原记忆 {len(result['restored'])} 条：{'、'.join(result['restored'])}")
    for item in result.get("not_restored") or []:
        lines.append(f"没有恢复 {item['id']}：{item['reason']}")
    lines.append(f"改主意了可重做：pmem archive --restore {result['id']}。记得提交 .memory/。")
    return "\n".join(lines)


def run_compact(root: Path, module: str, entity: str, min_size: int, as_json: bool, undo: str = "") -> int:
    service = MemoryService(root)
    try:
        if undo:
            result = service.revert(undo.strip())
        elif entity:
            if not module:
                print("--entity 需要和 --module 一起使用")
                return 2
            result = service.compact_group(module, entity)
        else:
            result = service.compact_groups(module or None, min_size)
    finally:
        service.close()
    if as_json or not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif undo:
        print(render_revert(result))
    else:
        print(render_group(result) if entity else render_groups(result))
    return 0 if result.get("ok") else 1
