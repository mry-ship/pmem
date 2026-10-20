"""pmem migrate：模块改名、合并、拆分、废弃、搬记忆（默认只预览，--apply 才写入）。规划逻辑在 pmem.catalog.migrate。"""
from __future__ import annotations

from pathlib import Path

from pmem.catalog.migrate import (
    MigrateError,
    apply_moves,
    merge_moves,
    pending_moves,
    plan_deprecate,
    plan_merge,
    plan_move,
    plan_rename,
    plan_split,
    stray_moves,
)
from pmem.catalog.yamlfile import ModulesFile
from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

MAX_LISTED = 10


def run_migrate(root: Path, action: str, first: str | None, second: str | None, apply: bool,
                undo: bool = False, targets: list[str] | None = None, by: str = "path",
                assigns: list[str] | None = None, ids: list[str] | None = None, keep_alias: bool = False) -> int:
    config = Config.load(root)
    if not config.modules_path.exists():
        print("还没有 .memory/modules.yaml，先按 pmem-bootstrap 技能划分模块")
        return 2
    file = ModulesFile.read(config.modules_path)
    data = file.data
    split = None
    try:
        registry = ModuleRegistry.load(config.modules_path)
        storage = FilesStorage(config.root, detect_vcs(config.root, config.get("vcs")), bool(config.get("svn_auto_add")))
        notes: list[str] = []
        new_data = data
        if action == "rename":
            new_data, notes = plan_rename(data, registry, first or "", second or "")
        elif action == "merge":
            new_data, notes = plan_merge(data, registry, first or "", second or "", keep_alias)
        elif action == "deprecate":
            new_data, notes = plan_deprecate(data, registry, first or "", undo)
        elif action == "split":
            split = plan_split(data, registry, storage, first or "", targets or [], by, assigns)
            new_data, notes = split.data, split.notes
        moves = plan_move(registry, storage, ids or [], second or "") if action == "move" else []
        if action == "merge":
            moves = merge_moves(registry, storage, first or "", second or "")
        new_registry = ModuleRegistry(new_data)
        moves = (split.moves if split else []) + moves
        planned = {m.entry_id for m in moves}
        moves += [m for m in stray_moves(storage, new_registry) if m.entry_id not in planned]
    except (MigrateError, RegistryError) as exc:
        print(f"无法迁移：{exc}")
        return 1

    for note in notes:
        print(note)
    if split and split.cross:
        print(f"关联代码横跨多个模块、留在原模块的记忆 {len(split.cross)} 条（不复制；要分走就加 --assign <id>=<模块>）：")
        for entry_id, owners in split.cross[:MAX_LISTED]:
            print(f"  {entry_id}：{' / '.join(owners)}")
    if split and split.unplaced:
        print(f"没有关联代码、同议题去向也不一致、留在原模块的记忆 {len(split.unplaced)} 条（需要时用 --assign 指定）：")
        print("  " + "、".join(split.unplaced[:MAX_LISTED]) + (" ……" if len(split.unplaced) > MAX_LISTED else ""))
    if moves:
        print(f"要搬动的记忆文件 {len(moves)} 个（文件里的模块名一并改为新名，id 和替代关系不变）：")
        for move in moves[:MAX_LISTED]:
            print(f"  {move.entry_id}：{move.source} → {move.target}")
        if len(moves) > MAX_LISTED:
            print(f"  ……另有 {len(moves) - MAX_LISTED} 个")
    elif action == "tidy":
        print("没有需要搬动的记忆文件：所有记忆都在正式模块名下")
        return 0
    lost = file.lost_comments() if new_data is not data else 0
    if lost:
        print(f"注意：modules.yaml 中间有 {lost} 行注释会在重写时丢失（文件开头的注释保留），提交前请看一眼 diff")

    if not apply:
        print("以上为预览；确认后加 --apply 执行")
        return 0
    if new_data is not data:
        file.write(new_data)
    try:
        apply_moves(storage, moves)
    except OSError as exc:
        print(f"搬动记忆文件中途失败：{exc}")
        if new_data is not data:
            print("modules.yaml 已更新，不要重新运行这次迁移")
        _print_recovery(storage, new_registry, moves)
        return 1
    print("已完成。运行 pmem doctor 检查路径重叠与覆盖率，然后提交 .memory/")
    return 0


def _print_recovery(storage: FilesStorage, registry: ModuleRegistry, moves: list) -> None:
    """tidy 只认得模块名已改名或并入的记忆；split、move 和未登记模块的合并要按 id 补搬。"""
    left = pending_moves(storage, moves)
    if not left:
        print("记忆文件其实都已搬完，运行 pmem doctor 检查后提交 .memory/")
        return
    try:
        by_tidy = {m.entry_id for m in stray_moves(storage, registry)}
    except MigrateError:
        by_tidy = set()
    manual: dict[str, list[str]] = {}
    for move in left:
        if move.entry_id not in by_tidy:
            manual.setdefault(move.target, []).append(move.entry_id)
    print(f"还有 {len(left)} 个记忆文件没搬完。排除问题后依次运行：")
    if any(m.entry_id in by_tidy for m in left):
        print("  pmem migrate tidy --apply")
    for target, ids in manual.items():
        print(f"  pmem migrate move {' '.join(ids)} --to {target} --apply")
