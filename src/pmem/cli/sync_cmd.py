"""pmem sync：对照代码目录列出 modules.yaml 的差异（默认只预览，--apply 只追加）。规划逻辑在 pmem.catalog.sync。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from pmem.catalog.sync import IDLE_DAYS, MODULE_MIN_FILES, SyncPlan, apply_plan, plan_sync
from pmem.catalog.yamlfile import ModulesFile
from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import HEAT_DAYS, file_heat_windows
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs


def render(plan: SyncPlan) -> list[str]:
    lines: list[str] = []

    def info(path: str) -> str:
        unit = path.removesuffix("/**")
        files, unit_heat = plan.unit_info.get(unit, (0, 0))
        return f"{path}（{files} 个代码文件，近 {HEAT_DAYS} 天改动 {unit_heat} 次）" if files else path

    if plan.new_modules:
        lines.append("新模块（大类按同目录的模块推测，不对就在 --apply 后用 pmem migrate rename 改）：")
        lines += [f"  {mid}：{'、'.join(info(p) for p in body['paths'])}" for mid, body in plan.new_modules.items()]
    if plan.new_candidates:
        lines.append(f"新冷候选（文件少于 {MODULE_MIN_FILES} 个或近期没有改动；有人写记忆或改动多了再转正）：")
        lines += [f"  {mid}：{'、'.join(info(p) for p in body['paths'])}" for mid, body in plan.new_candidates.items()]
    if plan.append_paths:
        lines.append("给已有模块追加路径（同名，或是它的又一个变体目录）：")
        lines += [f"  {mid} += {'、'.join(info(p) for p in paths)}" for mid, paths in plan.append_paths.items()]
    if plan.third_party:
        lines.append("新的第三方目录（追加到 third_party，不再计入覆盖率）：")
        lines += [f"  {p}" for p in plan.third_party]
    if plan.promote:
        lines.append("冷候选转正：")
        lines += [f"  {mid}：{why}" for mid, why in plan.promote]
    if plan.idle:
        lines.append(f"近 {IDLE_DAYS} 天没有改动、也没有记忆的模块（只是提示，不会自动改；"
                     "确实不再开发可以手工移到 candidates 或 pmem migrate merge 进伞形模块）：")
        lines.append("  " + "、".join(plan.idle[:20]) + (f" 等 {len(plan.idle)} 个" if len(plan.idle) > 20 else ""))
    if plan.loose:
        lines.append("已有模块目录里没被覆盖的零散文件（不会自动处理，需要时在对应模块的 paths 里补上）：")
        lines += [f"  {folder}（{n} 个文件）" for folder, n in plan.loose]
    if plan.conflicts:
        lines.append("与已有模块同名、未自动登记的目录（该模块已废弃或名字有歧义；"
                     "要恢复就 pmem migrate deprecate <模块> --undo，否则手工登记到别的模块）：")
        lines += [f"  {unit}/** ↔ {mid}" for unit, mid in plan.conflicts]
    if plan.split:
        lines.append("可以拆成子模块的目录（只是提示，不会自动改；要拆就运行后面的命令，记忆按关联代码跟着走）：")
        lines += [f"  {child}：{path}（{files} 个代码文件，近 {HEAT_DAYS} 天改动 {h} 次）\n"
                  f"    pmem migrate split {child.rsplit('.', 1)[0]} --to {child}={path}"
                  for child, path, files, h in plan.split]
    if not plan.history and lines:
        lines.append("注意：没有取到版本库提交历史，以上没有按改动热度区分新模块和冷候选，也不提示闲置模块")
    return lines


def run_sync(root: Path, apply: bool) -> int:
    config = Config.load(root)
    if not config.modules_path.exists():
        print("还没有 .memory/modules.yaml，先按 pmem-bootstrap 技能划分模块")
        return 2
    file = ModulesFile.read(config.modules_path)
    try:
        registry = ModuleRegistry.load(config.modules_path)
    except RegistryError as exc:
        print(f"无法同步：{exc}")
        return 1
    vcs = detect_vcs(config.root, config.get("vcs"))
    storage = FilesStorage(config.root, vcs)
    memories = Counter(e.module for _, e in storage.iter_all() if e.status != "archived")
    name, (heat, recent) = file_heat_windows(config.root, HEAT_DAYS, IDLE_DAYS, vcs=vcs)
    history = name != "none" and bool(heat or recent)
    plan = plan_sync(config.root, registry, memories, heat, recent, history=history)

    lines = render(plan)
    print("\n".join(lines) if lines else "modules.yaml 与代码目录一致，没有需要同步的内容")
    if not plan.changes:
        return 0
    lost = file.lost_comments()
    if lost:
        print(f"注意：modules.yaml 中间有 {lost} 行注释会在重写时丢失（文件开头的注释保留），提交前请看一眼 diff")
    if not apply:
        print("以上为预览；确认后加 --apply 写入 modules.yaml（只追加，不改已有模块名）")
        return 0
    new_data = apply_plan(file.data, plan)
    try:
        ModuleRegistry(new_data)
    except RegistryError as exc:
        print(f"无法同步：{exc}")
        return 1
    file.write(new_data)
    print("已写入 .memory/modules.yaml。运行 pmem doctor 检查覆盖率，然后提交 .memory/")
    return 0
