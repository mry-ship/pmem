"""pmem migrate：模块改名、合并、拆分、废弃，并把记忆文件搬到新模块下（默认只预览，--apply 才写入）。"""
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


def _check_new_name(registry: ModuleRegistry, new_id: str, own: str | None, merge_hint: str) -> None:
    """新模块名合法、大类存在、完整名和短名都没被别的模块占用（own 是允许占着短名的模块，如改名前的自己）。"""
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
                undo: bool = False, targets: list[str] | None = None, by: str = "path",
                assigns: list[str] | None = None) -> int:
    config = Config.load(root)
    path = config.modules_path
    if not path.exists():
        print("还没有 .memory/modules.yaml，先按 pmem-bootstrap 技能划分模块")
        return 2
    text = path.read_text(encoding="utf-8-sig")
    header, body = split_header(text)
    import yaml

    data = yaml.safe_load(body) or {}
    split = None
    try:
        registry = ModuleRegistry.load(path)
        storage = FilesStorage(config.root, detect_vcs(config.root, config.get("vcs")))
        if action == "rename":
            new_data, notes = plan_rename(data, registry, first or "", second or "")
        elif action == "merge":
            new_data, notes = plan_merge(data, registry, first or "", second or "")
        elif action == "deprecate":
            new_data, notes = plan_deprecate(data, registry, first or "", undo)
        elif action == "split":
            split = plan_split(data, registry, storage, first or "", targets or [], by, assigns)
            new_data, notes = split.data, split.notes
        else:
            new_data, notes = data, []
        new_registry = ModuleRegistry(new_data)
        moves = (split.moves if split else []) + stray_moves(storage, new_registry)
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
