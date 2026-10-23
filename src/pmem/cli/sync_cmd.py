"""pmem sync：对照代码目录列出 modules.yaml 的差异（默认只预览，--apply 只追加）。规划逻辑在 pmem.catalog.sync。"""
from __future__ import annotations

import time
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
    _lay_spec_skeletons(root)
    return 0


def run_auto_sync(root: Path, reason: str) -> int:
    from pmem.catalog.autosync import run_auto
    from pmem.core.autosync import count_text, counts, describe
    from pmem.metrics.events import log_event

    started = time.monotonic()
    result = run_auto(root, reason)
    status = result["status"]
    items = describe(result) if status == "found" else []
    if status != "off":
        n = counts(result) if status == "found" else {}
        log_event(Config.load(root).cache_dir, "autosync", reason=reason, status=status, full=result.get("full"),
                  applied=result.get("applied"), ms=round((time.monotonic() - started) * 1000),
                  **{k: v for k, v in n.items() if v})
    labels = {"off": "sync.auto 为 off，未扫描", "busy": "另一个自动扫描正在进行", "unchanged": "目录没有变化",
              "clean": "modules.yaml 与代码目录一致", "error": f"扫描出错：{result.get('error')}"}
    if status != "found":
        print(labels[status])
        return 1 if status == "error" else 0
    head = f"已自动登记，{count_text(result)}" if result.get("applied") else f"发现未登记目录，待{count_text(result)}"
    print(head + "：" + "；".join(items))
    if result.get("applied"):
        _lay_spec_skeletons(root)
    return 0


def _lay_spec_skeletons(root: Path) -> None:
    from pmem.cli.spec_cmd import ensure_spec_skeletons

    code, message = ensure_spec_skeletons(root)
    if not message:
        return
    print(message)
    if code == 0 and message.startswith("规格骨架") and "新写 0" not in message:
        print("还没有规格的模块只补了骨架。四份正文要对 Agent 说「补全模块规格」。")


def run_history(root: Path) -> int:
    from pmem.core.autosync import load_state

    history = load_state(Config.load(root).cache_dir).get("history") or []
    if not history:
        print("本机还没有自动登记过模块")
        return 0
    total = sum(h.get("new_modules", 0) for h in history), sum(h.get("new_candidates", 0) for h in history)
    print(f"最近 {len(history)} 次自动登记，共新增 {total[0]} 个模块、{total[1]} 个冷候选：")
    for h in reversed(history):
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(h.get("time") or 0))
        print(f"  {when}（{h.get('reason')}）新增 {h.get('new_modules', 0)} 个模块、{h.get('new_candidates', 0)} 个冷候选、"
              f"{h.get('append_paths', 0)} 个模块追加路径：{'、'.join(h.get('modules') or []) or '—'}")
    return 0
