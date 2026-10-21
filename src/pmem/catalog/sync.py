"""目录同步的规划：重新扫描代码目录，对照 modules.yaml 算出只追加的改动（不改已有模块名）。

- 新出现的业务目录 → 新模块，或冷候选（文件少、近期没改动）；
- 与已有模块同名、或是已有模块的又一个变体目录 → 给那个模块追加路径；
- 新出现的第三方目录 → 追加到 third_party；
- 冷候选改动多了或已经有人写了记忆 → 转正；
- 登记模块近 90 天没改动也没有记忆 → 只提示可以降为冷候选，不自动执行。
"""
from __future__ import annotations

import copy
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pmem.catalog.coverage import map_files
from pmem.core.registry import MAX_MODULE_DEPTH, WILDCARD, ModuleRegistry, RegistryError, module_depth
from pmem.scan.lite import HEAT_DAYS, THIRD_PARTY_NAMES

MODULE_MIN_FILES = 3
PROMOTE_HEAT = 5
SPLIT_MODULE_FILES = 60
SPLIT_CHILD_FILES = 30
IDLE_DAYS = 90
MIN_VARIANT_PATHS = 2
_WORD = re.compile(r"[A-Za-z0-9]+")


@dataclass
class SyncPlan:
    new_modules: dict[str, dict] = field(default_factory=dict)
    new_candidates: dict[str, dict] = field(default_factory=dict)
    append_paths: dict[str, list[str]] = field(default_factory=dict)
    third_party: list[str] = field(default_factory=list)
    promote: list[tuple[str, str]] = field(default_factory=list)
    idle: list[str] = field(default_factory=list)
    loose: list[tuple[str, int]] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    split: list[tuple[str, str, int, int]] = field(default_factory=list)
    unit_info: dict[str, tuple[int, int]] = field(default_factory=dict)
    history: bool = True

    @property
    def changes(self) -> bool:
        return bool(self.new_modules or self.new_candidates or self.append_paths or self.third_party or self.promote)


def pascal_name(folder: str) -> str | None:
    words = _WORD.findall(folder)
    name = "".join(w[:1].upper() + w[1:] for w in words)
    return name if name and name[0].isalpha() else None


def _dir_of(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _under(path: str, folder: str) -> bool:
    return not folder or path == folder or path.startswith(folder + "/")


def _scan(root: Path, registry: ModuleRegistry) -> tuple[dict[str, str], list[str]]:
    """代码文件 → 所属模块（含冷候选；路径重叠的记为空串，也算已覆盖），以及没被覆盖的文件。"""
    mapping = map_files(root, registry)
    return {**dict.fromkeys(mapping.conflicted, ""), **mapping.owner}, mapping.unmapped


def _units(owner: dict[str, str], unmapped: list[str]) -> tuple[dict[str, list[str]], Counter]:
    """没被覆盖的文件按“第一个里面完全没有已覆盖文件的上级目录”分组；上级目录全都有已覆盖文件的算散落文件。"""
    covered_dirs: set[str] = set()
    for rel in owner:
        parts = rel.split("/")[:-1]
        covered_dirs.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    units: dict[str, list[str]] = defaultdict(list)
    loose: Counter = Counter()
    for rel in unmapped:
        parts = rel.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            if prefix not in covered_dirs:
                units[prefix].append(rel)
                break
        else:
            loose[_dir_of(rel) or "（根目录）"] += 1
    return dict(units), loose


def _third_party_root(unit: str) -> str | None:
    parts = unit.split("/")
    for i, part in enumerate(parts):
        if THIRD_PARTY_NAMES.match(part):
            return "/".join(parts[: i + 1])
    return None


def _variant_owner(registry: ModuleRegistry, owner: dict[str, str], parent: str) -> str | None:
    """父目录下的已覆盖代码都属于同一个模块，且该模块已有至少两个路径挂在父目录的直接子目录上：新目录是它的又一个变体。"""
    if not parent:
        return None
    owners = {mid for rel, mid in owner.items() if _under(rel, parent)}
    if len(owners) != 1:
        return None
    mid = next(iter(owners))
    module = registry.modules.get(mid) or registry.candidates.get(mid)
    # 已废弃的模块只读，新目录不能再挂到它上面
    if not mid or module is None or module.deprecated:
        return None
    prefix = parent.lower().split("/")
    children = 0
    for pattern in module.paths:
        parts = pattern.replace("\\", "/").lower().split("/")
        if len(parts) > len(prefix) and parts[:len(prefix)] == prefix and not WILDCARD.search(parts[len(prefix)]):
            children += 1
    return mid if children >= MIN_VARIANT_PATHS else None


def _guess_category(registry: ModuleRegistry, owner: dict[str, str], parent: str) -> str:
    near = Counter(mid.split(".", 1)[0] for rel, mid in owner.items() if mid and _under(rel, parent))
    if parent and near:
        return near.most_common(1)[0][0]
    overall = Counter(mid.split(".", 1)[0] for mid in registry.modules)
    if overall:
        return overall.most_common(1)[0][0]
    return registry.categories[0]


def _existing_module(registry: ModuleRegistry, name: str) -> str | None:
    try:
        resolved = registry.resolve_module(name)
    except RegistryError:
        resolved = None
    if resolved is not None and resolved.known:
        module = registry.modules[resolved.id]
        return None if module.deprecated else resolved.id
    if resolved is not None and resolved.candidate:
        return resolved.id
    # 短名只索引正式模块，同名的冷候选要单独找
    same = [cid for cid in registry.candidates if cid.rsplit(".", 1)[-1].lower() == name.lower()]
    return same[0] if len(same) == 1 else None


def _expand(registry: ModuleRegistry, unit: str, files: list[str]) -> dict[str, list[str]]:
    """UI/、Views/ 这类技术层目录：子目录里有和已有模块同名的，就拆成各个子目录分别处理，而不是整个当成一个模块。"""
    children: dict[str, list[str]] = defaultdict(list)
    direct: list[str] = []
    for rel in files:
        rest = rel[len(unit) + 1:].split("/")
        (children[f"{unit}/{rest[0]}"] if len(rest) > 1 else direct).append(rel)
    if not any(_existing_module(registry, pascal_name(c.rsplit("/", 1)[-1]) or "") for c in children):
        return {unit: files}
    result: dict[str, list[str]] = {}
    for child, child_files in children.items():
        result.update(_expand(registry, child, child_files))
    if direct:
        result[unit] = direct
    return result


def plan_sync(root: Path, registry: ModuleRegistry, memories: Counter,
              heat: Counter, recent: Counter, history: bool = True) -> SyncPlan:
    """history=False（没有版本库或取不到提交历史）时热度全是 0：不按热度分新模块和冷候选，也不提示闲置模块。"""
    plan = SyncPlan(history=history)
    taken_ids = {mid.lower(): mid for mid in (*registry.modules, *registry.candidates)}
    owner, unmapped = _scan(root, registry)
    raw_units, loose = _units(owner, unmapped)
    units: dict[str, list[str]] = {}
    for unit, files in raw_units.items():
        units.update(_expand(registry, unit, files))
    plan.loose = loose.most_common(10)
    taken: dict[str, str] = {}
    for unit in sorted(units):
        files = units[unit]
        unit_heat = sum(heat.get(f, 0) for f in files)
        plan.unit_info[unit] = (len(files), unit_heat)
        third = _third_party_root(unit)
        if third:
            if third not in plan.third_party:
                plan.third_party.append(third)
            continue
        path = f"{unit}/**"
        parent = _dir_of(unit)
        name = pascal_name(unit.rsplit("/", 1)[-1])
        target = _variant_owner(registry, owner, parent) or (name and _existing_module(registry, name))
        if not target and name and name.lower() in taken:
            target = taken[name.lower()]
        if target:
            if target in plan.new_modules or target in plan.new_candidates:
                pool = plan.new_modules if target in plan.new_modules else plan.new_candidates
                pool[target]["paths"].append(path)
            else:
                plan.append_paths.setdefault(target, []).append(path)
            continue
        if not name:
            plan.loose.append((unit, len(files)))
            continue
        mid = f"{_guess_category(registry, owner, parent)}.{name}"
        if mid.lower() in taken_ids:
            # 只可能是已废弃（只读）的同名模块：自动追加或新建都会把新代码挂到只读模块上，甚至整段覆盖它
            plan.conflicts.append((unit, taken_ids[mid.lower()]))
            continue
        body = {"paths": [path], "origin": "sync"}
        if len(files) >= MODULE_MIN_FILES and (unit_heat > 0 or not history):
            plan.new_modules[mid] = body
        else:
            plan.new_candidates[mid] = body
        taken[name.lower()] = mid

    by_module: dict[str, list[str]] = defaultdict(list)
    for rel, mid in owner.items():
        if mid:
            by_module[mid].append(rel)
    for mid, cand in registry.candidates.items():
        if cand.merged_into:
            continue
        cand_heat = sum(heat.get(f, 0) for f in by_module.get(mid, []))
        if memories.get(mid):
            plan.promote.append((mid, f"已有 {memories[mid]} 条记忆"))
        elif cand_heat >= PROMOTE_HEAT:
            plan.promote.append((mid, f"近 {HEAT_DAYS} 天改动 {cand_heat} 次"))
    plan.split = _split_proposals(registry, by_module, heat, taken_ids)
    if not history:
        return plan
    for mid, module in sorted(registry.modules.items()):
        files = by_module.get(mid, [])
        if module.merged_into or module.deprecated or not files or memories.get(mid):
            continue
        if not any(recent.get(f, 0) for f in files):
            plan.idle.append(mid)
    return plan


def _split_proposals(registry: ModuleRegistry, by_module: dict[str, list[str]], heat: Counter,
                     taken_ids: dict[str, str]) -> list[tuple[str, str, int, int]]:
    """大模块（≥60 个文件）里文件多或改动多的直接子目录，提议拆成子模块：(子模块, 路径, 文件数, 热度)。只提示，不自动执行。"""
    proposals: list[tuple[str, str, int, int]] = []
    for mid, module in sorted(registry.modules.items()):
        files = by_module.get(mid, [])
        if module.merged_into or module.deprecated or len(files) < SPLIT_MODULE_FILES:
            continue
        if module_depth(mid) >= MAX_MODULE_DEPTH:
            continue
        for pattern in module.paths:
            pattern = pattern.replace("\\", "/")
            base = pattern.removesuffix("/**")
            if base == pattern or WILDCARD.search(base):
                continue
            groups: dict[str, list[str]] = defaultdict(list)
            for rel in files:
                rest = rel[len(base) + 1:].split("/") if rel.startswith(base + "/") else []
                if len(rest) > 1:
                    groups[rest[0]].append(rel)
            for folder, sub in sorted(groups.items()):
                sub_heat = sum(heat.get(f, 0) for f in sub)
                name = pascal_name(folder)
                if not name or len(sub) < MODULE_MIN_FILES:
                    continue
                if len(sub) < SPLIT_CHILD_FILES and sub_heat < PROMOTE_HEAT:
                    continue
                child = f"{mid}.{name}"
                if child.lower() not in taken_ids:
                    proposals.append((child, f"{base}/{folder}/**", len(sub), sub_heat))
    return proposals


def apply_plan(data: dict, plan: SyncPlan) -> dict:
    out = copy.deepcopy(data)
    modules = out.setdefault("modules", {}) or {}
    out["modules"] = modules
    candidates = out.get("candidates") or {}
    for mid, extra in plan.append_paths.items():
        pool = modules if mid in modules else candidates
        body = dict(pool.get(mid) or {})
        paths = list(body.get("paths") or [])
        paths += [p for p in extra if p not in paths]
        body["paths"] = paths
        pool[mid] = body
    for mid, _ in plan.promote:
        if mid in candidates:
            modules[mid] = candidates.pop(mid) or {}
    # 只追加：已有的键（含废弃模块）一律不覆盖
    for mid, body in plan.new_modules.items():
        if mid not in modules and mid not in candidates:
            modules[mid] = copy.deepcopy(body)
    for mid, body in plan.new_candidates.items():
        if mid not in modules and mid not in candidates:
            candidates[mid] = copy.deepcopy(body)
    if candidates or "candidates" in out:
        out["candidates"] = candidates
    if plan.third_party:
        third = list(out.get("third_party") or [])
        third += [p for p in plan.third_party if p not in third]
        out["third_party"] = third
    return out
