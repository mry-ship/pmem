"""pmem migrate：模块改名、合并、废弃，并把记忆文件搬到新模块下（默认只预览，--apply 才写入）。"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path

from pmem.core.config import Config
from pmem.core.registry import DEPRECATED, ModuleRegistry, RegistryError
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*$")
_MERGED_PREFIX = "merged_into:"
MAX_LISTED = 10


class MigrateError(ValueError):
    pass


@dataclass
class Move:
    path: Path
    entry_id: str
    source: str
    target: str


def split_header(text: str) -> tuple[str, str]:
    """文件开头的注释块原样保留；之后的注释在重写时会丢失，所以单独返回正文统计。"""
    lines = text.splitlines(keepends=True)
    cut = 0
    while cut < len(lines) and (not lines[cut].strip() or lines[cut].lstrip().startswith("#")):
        cut += 1
    return "".join(lines[:cut]), "".join(lines[cut:])


def body_comments(body: str) -> int:
    return sum(1 for line in body.splitlines() if line.lstrip().startswith("#") or " #" in line)


def dump_modules(header: str, data: dict) -> str:
    import yaml

    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
    return header + text


def _module_key(data: dict, registry: ModuleRegistry, raw: str) -> str:
    resolved = registry.resolve_module(raw)
    if not resolved.known:
        raise MigrateError(f"{raw} 不是 modules.yaml 里登记的模块")
    if resolved.redirected_from:
        raise MigrateError(f"{resolved.redirected_from} 已并入 {resolved.id}，不能再迁移它")
    mid = resolved.id
    if mid not in (data.get("modules") or {}):
        raise MigrateError(f"{raw} 是别名，请写模块的正式名字 {mid}")
    return mid


def _merge_list(target: dict, key: str, values: list) -> None:
    merged = list(target.get(key) or [])
    seen = {str(v).lower() for v in merged}
    for value in values or []:
        if str(value).lower() not in seen:
            merged.append(value)
            seen.add(str(value).lower())
    if merged:
        target[key] = merged


def _free_bare_name(registry: ModuleRegistry, old_id: str, new_id: str) -> list[str]:
    """旧的短名（不带大类）只被旧模块使用时也登记为别名，正文提及和短名检索才能继续认出它。"""
    bare = old_id.split(".", 1)[1]
    if bare.lower() == new_id.split(".", 1)[1].lower():
        return []
    try:
        owner = registry.resolve_module(bare).id
    except RegistryError:
        return []
    return [bare] if owner == old_id else []


def plan_rename(data: dict, registry: ModuleRegistry, old: str, new: str) -> tuple[dict, list[str]]:
    old_id = _module_key(data, registry, old)
    new_id = new.strip()
    if not _NAME_RE.match(new_id):
        raise MigrateError(f"新名字 {new_id!r} 不合法，格式为 category.Name（大类小写，模块名字母开头）")
    if new_id.split(".", 1)[0] not in registry.categories:
        raise MigrateError(f"大类 {new_id.split('.', 1)[0]!r} 不存在，只允许：{' / '.join(registry.categories)}")
    try:
        taken = registry.resolve_module(new_id)
    except RegistryError:
        taken = None
    if taken is not None and taken.known:
        raise MigrateError(f"{new_id} 已经是模块 {taken.id} 的名字或别名")
    if taken is not None and taken.candidate:
        raise MigrateError(f"{new_id} 是冷候选模块，请改用 pmem migrate merge {new_id} {old_id}")
    bare = new_id.split(".", 1)[1]
    try:
        owner = registry.resolve_module(bare).id
    except RegistryError:
        owner = None
    if owner is not None and owner != old_id:
        raise MigrateError(f"短名 {bare} 已是模块 {owner} 的名字或别名，改名后会有歧义")

    out = copy.deepcopy(data)
    modules: dict = {}
    for mid, body in (out.get("modules") or {}).items():
        if mid != old_id:
            modules[mid] = body
            continue
        body = dict(body or {})
        _merge_list(body, "aliases", [old_id, *_free_bare_name(registry, old_id, new_id)])
        modules[new_id] = body
    for body in [*modules.values(), *(out.get("candidates") or {}).values()]:
        if not isinstance(body, dict):
            continue
        if str(body.get("status") or "").strip() == f"{_MERGED_PREFIX}{old_id}":
            body["status"] = f"{_MERGED_PREFIX}{new_id}"
        if body.get("parent") == old_id:
            body["parent"] = new_id
    out["modules"] = modules
    return out, [f"{old_id} 改名为 {new_id}，旧名登记为别名，读写自动转到新名"]


def _plan_merge_unregistered(data: dict, registry: ModuleRegistry, source: str, dst_id: str) -> tuple[dict, list[str]]:
    """写入时自动新建（未登记）或冷候选模块并入正式模块：登记为目标的别名，之后的写入也自动转过去。"""
    resolved = registry.resolve_module(source)
    src_id = resolved.id
    out = copy.deepcopy(data)
    dst = dict(out["modules"][dst_id] or {})
    _merge_list(dst, "aliases", [src_id])
    notes = [f"{src_id}（未登记）并入 {dst_id}：登记为 {dst_id} 的别名"]
    candidates = out.get("candidates") or {}
    if resolved.candidate and src_id in candidates:
        body = candidates.pop(src_id) or {}
        _merge_list(dst, "paths", body.get("paths") or [])
        notes = [f"冷候选 {src_id} 并入 {dst_id}：路径并入目标模块，名字登记为别名"]
    out["modules"][dst_id] = dst
    return out, notes


def plan_merge(data: dict, registry: ModuleRegistry, source: str, target: str) -> tuple[dict, list[str]]:
    out, notes = _plan_merge(data, registry, source, target)
    dst_id = _module_key(data, registry, target)
    if registry.modules[dst_id].deprecated:
        notes.append(f"注意：{dst_id} 已废弃，并入后这些记忆同样只读")
    return out, notes


def _plan_merge(data: dict, registry: ModuleRegistry, source: str, target: str) -> tuple[dict, list[str]]:
    dst_id = _module_key(data, registry, target)
    if not registry.resolve_module(source).known:
        return _plan_merge_unregistered(data, registry, source, dst_id)
    src_id = _module_key(data, registry, source)
    if src_id == dst_id:
        raise MigrateError("不能把模块合并到它自己")

    out = copy.deepcopy(data)
    modules = out["modules"]
    src = dict(modules[src_id] or {})
    dst = dict(modules[dst_id] or {})
    for key in ("paths", "aliases", "entities", "components", "variants"):
        _merge_list(dst, key, src.get(key) or [])
    kept = {k: v for k, v in src.items() if k == "description"}
    modules[src_id] = {**kept, "status": f"{_MERGED_PREFIX}{dst_id}"}
    modules[dst_id] = dst
    notes = [f"{src_id} 并入 {dst_id}：路径、别名、议题并入目标模块，{src_id} 标为 merged_into，读写自动转到 {dst_id}"]
    if src.get("paths"):
        notes.append(f"{dst_id} 新增路径：{', '.join(map(str, src['paths']))}")
    return out, notes


def plan_deprecate(data: dict, registry: ModuleRegistry, module: str, undo: bool) -> tuple[dict, list[str]]:
    mid = _module_key(data, registry, module)
    deprecated = registry.modules[mid].deprecated
    if deprecated != undo:
        raise MigrateError(f"{mid} {'没有' if undo else '已经'}废弃")
    out = copy.deepcopy(data)
    body = dict(out["modules"][mid] or {})
    if undo:
        body.pop("status", None)
        notes = [f"{mid} 恢复为正常模块，重新接受新记忆"]
    else:
        body["status"] = DEPRECATED
        notes = [(f"{mid} 标为废弃：旧记忆照常可查，拒绝新写入，改完代码不再提醒写记忆；"
                  "路径仍归它，改这些代码前照样要先查记忆")]
    out["modules"][mid] = body
    return out, notes


def stray_moves(storage: FilesStorage, registry: ModuleRegistry) -> list[Move]:
    """记忆文件里的模块名已改名或并入别的模块时，需要搬到的位置。"""
    moves = []
    for path, entry in storage.iter_all():
        try:
            resolved = registry.resolve_module(entry.module)
        except RegistryError:
            continue
        if not resolved.known or resolved.id == entry.module:
            continue
        dst = storage.entries_dir / resolved.id / path.name
        if dst.exists() and not dst.samefile(path):
            raise MigrateError(f"{dst} 已存在，与 {path} 同名，先手动处理重复的记忆文件")
        moves.append(Move(path, entry.id, entry.module, resolved.id))
    return moves


def apply_moves(storage: FilesStorage, moves: list[Move]) -> None:
    for move in moves:
        entry = storage.read(move.path)
        entry.module = move.target
        dst = storage.entries_dir / move.target / move.path.name
        if dst != move.path:
            storage.vcs.move(move.path, dst)
        dst.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
        folder = move.path.parent
        if storage.vcs.name != "svn" and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()


def run_migrate(root: Path, action: str, first: str | None, second: str | None, apply: bool,
                undo: bool = False) -> int:
    config = Config.load(root)
    path = config.modules_path
    if not path.exists():
        print("还没有 .memory/modules.yaml，先按 pmem-bootstrap 技能划分模块")
        return 2
    text = path.read_text(encoding="utf-8-sig")
    header, body = split_header(text)
    import yaml

    data = yaml.safe_load(body) or {}
    try:
        registry = ModuleRegistry.load(path)
        if action == "rename":
            new_data, notes = plan_rename(data, registry, first or "", second or "")
        elif action == "merge":
            new_data, notes = plan_merge(data, registry, first or "", second or "")
        elif action == "deprecate":
            new_data, notes = plan_deprecate(data, registry, first or "", undo)
        else:
            new_data, notes = data, []
        new_registry = ModuleRegistry(new_data)
        storage = FilesStorage(config.root, detect_vcs(config.root, config.get("vcs")))
        moves = stray_moves(storage, new_registry)
    except (MigrateError, RegistryError) as exc:
        print(f"无法迁移：{exc}")
        return 1

    for note in notes:
        print(note)
    if moves:
        print(f"要搬动的记忆文件 {len(moves)} 个（文件里的模块名一并改为新名，id 和替代关系不变）：")
        for move in moves[:MAX_LISTED]:
            print(f"  {move.entry_id}：{move.source} → {move.target}")
        if len(moves) > MAX_LISTED:
            print(f"  ……另有 {len(moves) - MAX_LISTED} 个")
    elif action == "tidy":
        print("没有需要搬动的记忆文件：所有记忆都在正式模块名下")
        return 0
    lost = body_comments(body) if new_data is not data else 0
    if lost:
        print(f"注意：modules.yaml 中间有 {lost} 行注释会在重写时丢失（文件开头的注释保留），提交前请看一眼 diff")

    if not apply:
        print("以上为预览；确认后加 --apply 执行")
        return 0
    if new_data is not data:
        path.write_text(dump_modules(header, new_data), encoding="utf-8", newline="\n")
    try:
        apply_moves(storage, moves)
    except OSError as exc:
        print(f"搬动记忆文件中途失败：{exc}\nmodules.yaml 已更新；排除问题后运行 pmem migrate tidy --apply 搬完剩下的")
        return 1
    print("已完成。运行 pmem doctor 检查路径重叠与覆盖率，然后提交 .memory/")
    return 0
