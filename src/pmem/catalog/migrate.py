"""模块迁移的规划与执行：改名、合并、拆分、废弃，以及把记忆文件搬到新模块下。只算出新的 modules.yaml 内容和要搬的文件，写入由调用方决定。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml

from pmem.core.registry import DEPRECATED, MERGED_PREFIX, ModuleRegistry, RegistryError, is_module_id
from pmem.storage.files import FilesStorage


class MigrateError(ValueError):
    pass


@dataclass
class Move:
    path: Path
    entry_id: str
    source: str
    target: str


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


def _check_new_name(registry: ModuleRegistry, new_id: str, own: str | None, merge_hint: str) -> None:
    """新模块名合法、大类存在、完整名和短名都没被别的模块占用（own 是允许占着短名的模块，如改名前的自己）。"""
    if not is_module_id(new_id):
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
        raise MigrateError(f"{new_id} 是冷候选模块，{merge_hint}")
    bare = new_id.split(".", 1)[1]
    try:
        owner = registry.resolve_module(bare).id
    except RegistryError:
        owner = None
    if owner is not None and owner != own:
        raise MigrateError(f"短名 {bare} 已是模块 {owner} 的名字或别名，会有歧义")


def plan_rename(data: dict, registry: ModuleRegistry, old: str, new: str) -> tuple[dict, list[str]]:
    old_id = _module_key(data, registry, old)
    new_id = new.strip()
    _check_new_name(registry, new_id, old_id, f"请改用 pmem migrate merge {new_id} {old_id}")

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
        if str(body.get("status") or "").strip() == f"{MERGED_PREFIX}{old_id}":
            body["status"] = f"{MERGED_PREFIX}{new_id}"
        if body.get("parent") == old_id:
            body["parent"] = new_id
    out["modules"] = modules
    return out, [f"{old_id} 改名为 {new_id}，旧名登记为别名，读写自动转到新名"]


def _plan_merge_unregistered(data: dict, registry: ModuleRegistry, source: str, dst_id: str,
                             keep_alias: bool) -> tuple[dict, list[str]]:
    """写入时自动新建（未登记）或冷候选模块并入正式模块。
    冷候选的名字登记为目标的别名；未登记的多半是笔误，只有 keep_alias 时才登记，否则只搬记忆。"""
    resolved = registry.resolve_module(source)
    src_id = resolved.id
    out = copy.deepcopy(data)
    candidates = out.get("candidates") or {}
    is_candidate = resolved.candidate and src_id in candidates
    if not is_candidate and not keep_alias:
        ask = (f"{src_id} 是以后还会这样写的叫法吗？是就加 --alias 把它登记为 {dst_id} 的别名，"
               "之后写到这个名字会自动转过去；只是笔误就不用加")
        return out, [f"{src_id}（未登记）的记忆搬到 {dst_id}，不登记为别名。", ask]
    dst = dict(out["modules"][dst_id] or {})
    _merge_list(dst, "aliases", [src_id])
    notes = [f"{src_id}（未登记）并入 {dst_id}：登记为 {dst_id} 的别名"]
    if is_candidate:
        body = candidates.pop(src_id) or {}
        _merge_list(dst, "paths", body.get("paths") or [])
        notes = [f"冷候选 {src_id} 并入 {dst_id}：路径并入目标模块，名字登记为别名"]
    out["modules"][dst_id] = dst
    return out, notes


def plan_merge(data: dict, registry: ModuleRegistry, source: str, target: str,
               keep_alias: bool = False) -> tuple[dict, list[str]]:
    out, notes = _plan_merge(data, registry, source, target, keep_alias)
    dst_id = _module_key(data, registry, target)
    if registry.modules[dst_id].deprecated:
        notes.append(f"注意：{dst_id} 已废弃，并入后这些记忆同样只读")
    return out, notes


def merge_moves(registry: ModuleRegistry, storage: FilesStorage, source: str, target: str) -> list[Move]:
    """未登记模块并入时不一定登记别名，stray_moves 认不出它的记忆，按模块名直接列出要搬的文件。"""
    resolved = registry.resolve_module(source)
    if resolved.known:
        return []
    dst_id = registry.resolve_module(target).id
    return [Move(path, entry.id, entry.module, dst_id)
            for path, entry in storage.iter_all() if entry.module.lower() == resolved.id.lower()]


def _plan_merge(data: dict, registry: ModuleRegistry, source: str, target: str,
                keep_alias: bool) -> tuple[dict, list[str]]:
    dst_id = _module_key(data, registry, target)
    if not registry.resolve_module(source).known:
        return _plan_merge_unregistered(data, registry, source, dst_id, keep_alias)
    src_id = _module_key(data, registry, source)
    if keep_alias:
        raise MigrateError(f"--alias 只用于未登记的模块；{src_id} 已登记，并入后旧名会自动转到 {dst_id}")
    if src_id == dst_id:
        raise MigrateError("不能把模块合并到它自己")

    out = copy.deepcopy(data)
    modules = out["modules"]
    src = dict(modules[src_id] or {})
    dst = dict(modules[dst_id] or {})
    for key in ("paths", "aliases", "entities", "components", "variants"):
        _merge_list(dst, key, src.get(key) or [])
    kept = {k: v for k, v in src.items() if k == "description"}
    modules[src_id] = {**kept, "status": f"{MERGED_PREFIX}{dst_id}"}
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


@dataclass
class SplitPlan:
    data: dict
    notes: list[str]
    moves: list[Move]
    cross: list[tuple[str, list[str]]]
    unplaced: list[str]


def _parse_targets(targets: list[str]) -> list[tuple[str, list[str]]]:
    parsed = []
    for raw in targets:
        name, sep, specs = raw.partition("=")
        items = [s.strip() for s in specs.split(",") if s.strip()]
        if not sep or not name.strip() or not items:
            raise MigrateError(f"--to {raw!r} 格式不对，应为 新模块=路径或议题[,路径或议题...]")
        parsed.append((name.strip(), items))
    return parsed


def _module_list(data: dict, mid: str, key: str) -> list:
    return list(((data.get("modules") or {}).get(mid) or {}).get(key) or [])


def _anchor_path(anchor: str) -> str:
    return anchor.split("#", 1)[0].strip()


def plan_split(data: dict, registry: ModuleRegistry, storage: FilesStorage, source: str, targets: list[str],
               by: str = "path", assigns: list[str] | None = None) -> SplitPlan:
    """把 source 的一部分路径（--by path）或议题（--by entity）分给新模块或已有模块，并按同样的规则分配记忆。

    记忆归属：--assign 指定的优先；按路径拆时看关联代码在新目录里归谁，关联代码横跨多个模块的不复制、留在原模块；
    没有关联代码的跟着同议题的其他记忆走，同议题的去向不一致时留在原模块。按议题拆时直接看 entity。
    """
    from pmem.scan.lite import iter_code_files

    src_id = _module_key(data, registry, source)
    if by not in ("path", "entity"):
        raise MigrateError("--by 只能是 path 或 entity")
    parsed = _parse_targets(targets)
    if not parsed:
        raise MigrateError("至少要给一个 --to 新模块=路径或议题")
    out = copy.deepcopy(data)
    modules = out["modules"]
    src = dict(modules[src_id] or {})
    notes: list[str] = []
    target_ids: list[str] = []
    claimed: dict[str, str] = {}
    entity_owner: dict[str, str] = {}
    for raw_name, specs in parsed:
        resolved = None
        try:
            resolved = registry.resolve_module(raw_name)
        except RegistryError:
            pass
        if resolved is not None and resolved.known:
            tid = _module_key(data, registry, raw_name)
            if tid == src_id:
                raise MigrateError("不能把模块拆给它自己")
            if registry.modules[tid].deprecated:
                notes.append(f"注意：{tid} 已废弃，分过去的记忆同样只读")
            body = dict(modules[tid] or {})
        else:
            tid = raw_name
            _check_new_name(registry, tid, None, f"请先 pmem migrate merge {tid} <正式模块> 或换个名字")
            if tid in target_ids:
                raise MigrateError(f"{tid} 重复出现，请把它的路径或议题写在同一个 --to 里")
            body = {}
        target_ids.append(tid)
        for spec in specs:
            key = spec.replace("\\", "/").lower()
            if key in claimed:
                raise MigrateError(f"{spec} 同时分给了 {claimed[key]} 和 {tid}")
            claimed[key] = tid
        if by == "entity":
            lists = {k: list(src.get(k) or []) for k in ("entities", "components", "variants")}
            for spec in specs:
                entity_owner[spec.lower()] = tid
                for k, values in lists.items():
                    src[k] = [v for v in values if str(v).lower() != spec.lower()]
                    lists[k] = src[k]
            _merge_list(body, "entities", specs)
            notes.append(f"{tid} ← 议题 {'、'.join(specs)}")
        else:
            src_paths = list(src.get("paths") or [])
            for spec in specs:
                exact = [p for p in src_paths if str(p).replace("\\", "/").lower() == spec.replace("\\", "/").lower()]
                src_paths = [p for p in src_paths if p not in exact]
            src["paths"] = src_paths
            _merge_list(body, "paths", specs)
            notes.append(f"{tid} ← 路径 {'、'.join(specs)}")
        modules[tid] = body
    for key in ("entities", "components", "variants", "paths"):
        if key in src and not src[key]:
            del src[key]
    modules[src_id] = src
    try:
        new_registry = ModuleRegistry(out)
    except RegistryError as exc:
        raise MigrateError(str(exc)) from exc

    if by == "path":
        moved: set[str] = set()
        for rel in iter_code_files(storage.root):
            try:
                before = registry.module_for_path(rel)
                after = new_registry.module_for_path(rel)
            except RegistryError as exc:
                raise MigrateError(str(exc)) from exc
            if after is None or after.module_id not in target_ids:
                continue
            was = before.module_id if before else None
            if was == src_id:
                moved.add(after.module_id)
            elif was not in (None, after.module_id):
                raise MigrateError(f"{rel} 原本属于 {was}，不在 {src_id} 里，不能分给 {after.module_id}")
        empty = [t for t in target_ids if t not in moved]
        if empty:
            raise MigrateError(f"{'、'.join(empty)} 分到的路径下没有 {src_id} 的代码文件，检查路径写法（如 src/Foo/**）")

    manual: dict[str, str] = {}
    for raw in assigns or []:
        entry_id, sep, mid = raw.partition("=")
        if not sep or mid.strip() not in (src_id, *target_ids):
            raise MigrateError(f"--assign {raw!r} 格式不对，应为 记忆id=模块，模块只能是 {src_id} 或拆出的模块")
        manual[entry_id.strip()] = mid.strip()

    entries = [(path, e) for path, e in storage.iter_all() if e.module == src_id]
    if by == "entity":
        known = {str(v).lower() for k in ("entities", "components", "variants") for v in _module_list(data, src_id, k)}
        known |= {e.entity.lower() for _, e in entries}
        missing = [spec for spec in entity_owner if spec not in known]
        if missing:
            raise MigrateError(f"{src_id} 里没有议题 {'、'.join(missing)}（modules.yaml 的 entities 和记忆里都没有），检查拼写")
    unknown = set(manual) - {e.id for _, e in entries}
    if unknown:
        raise MigrateError(f"--assign 里的记忆不在 {src_id} 下：{'、'.join(sorted(unknown))}")
    dest: dict[str, str] = {}
    cross: list[tuple[str, list[str]]] = []
    pending: list[tuple[Path, object]] = []
    for path, entry in entries:
        if entry.id in manual:
            dest[entry.id] = manual[entry.id]
        elif by == "entity":
            dest[entry.id] = entity_owner.get(entry.entity.lower(), src_id)
        else:
            owners = set()
            for anchor in entry.anchors:
                try:
                    match = new_registry.module_for_path(_anchor_path(anchor))
                except RegistryError:
                    match = None
                if match:
                    owners.add(match.module_id)
            if not owners:
                pending.append((path, entry))
            elif len(owners) == 1:
                only = next(iter(owners))
                dest[entry.id] = only if only in target_ids else src_id
            else:
                dest[entry.id] = src_id
                if owners & set(target_ids):
                    cross.append((entry.id, sorted(owners)))
    cross_ids = {entry_id for entry_id, _ in cross}
    unplaced: list[str] = []
    by_entity: dict[str, set[str]] = {}
    for _, entry in entries:
        if entry.id in dest and entry.id not in cross_ids:
            by_entity.setdefault(entry.entity.lower(), set()).add(dest[entry.id])
    for _, entry in pending:
        follow = by_entity.get(entry.entity.lower(), set())
        if len(follow) == 1:
            dest[entry.id] = next(iter(follow))
        else:
            dest[entry.id] = src_id
            unplaced.append(entry.id)
    moves = [Move(path, e.id, src_id, dest[e.id]) for path, e in entries if dest.get(e.id, src_id) != src_id]
    counts = {t: sum(1 for m in moves if m.target == t) for t in target_ids}
    notes.append(f"{src_id} 的记忆 {len(entries)} 条：" + "，".join(f"分给 {t} {n} 条" for t, n in counts.items())
                 + f"，留在 {src_id} {len(entries) - len(moves)} 条")
    return SplitPlan(out, notes, moves, cross, unplaced)


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


def plan_move(registry: ModuleRegistry, storage: FilesStorage, ids: list[str], target: str) -> list[Move]:
    """把归错模块的记忆按 id 搬到另一个正式模块；id、替代关系和关联代码都不变。"""
    try:
        resolved = registry.resolve_module(target)
    except RegistryError as exc:
        raise MigrateError(str(exc)) from exc
    if not resolved.known:
        raise MigrateError(f"{target} 不是 modules.yaml 里登记的模块")
    if registry.modules[resolved.id].deprecated:
        raise MigrateError(f"{resolved.id} 已废弃（只读），不能再往里搬记忆")
    if not ids:
        raise MigrateError("至少给一个记忆 id")
    moves = []
    for entry_id in dict.fromkeys(ids):
        path = storage.find_path(entry_id)
        if path is None:
            raise MigrateError(f"找不到记忆 {entry_id}")
        entry = storage.read(path)
        if entry.module == resolved.id:
            raise MigrateError(f"记忆 {entry_id} 已经在 {resolved.id} 下")
        moves.append(Move(path, entry.id, entry.module, resolved.id))
    return moves


def pending_moves(storage: FilesStorage, moves: list[Move]) -> list[Move]:
    """搬动中途失败后还没完成的部分：记忆文件里的模块名还不是目标名（文件已移走但没改写也算）。"""
    left = []
    for move in moves:
        path = storage.find_path(move.entry_id)
        if path is None:
            continue
        try:
            module = storage.read(path).module
        except (OSError, ValueError, yaml.YAMLError):
            module = move.source
        if module != move.target:
            left.append(Move(path, move.entry_id, module, move.target))
    return left


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
