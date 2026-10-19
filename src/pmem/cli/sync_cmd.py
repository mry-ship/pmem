"""pmem sync：重新扫描代码目录，对照 modules.yaml 列出差异（默认只预览，--apply 只追加，不改已有模块名）。

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

from pmem.cli.migrate_cmd import body_comments, dump_modules, split_header
from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import HEAT_DAYS, THIRD_PARTY_NAMES, file_heat_windows, iter_code_files
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

MODULE_MIN_FILES = 3
PROMOTE_HEAT = 5
IDLE_DAYS = 90
MIN_VARIANT_PATHS = 2
_WORD = re.compile(r"[A-Za-z0-9]+")
_WILDCARD = re.compile(r"[*?\[{]")


@dataclass
class SyncPlan:
    new_modules: dict[str, dict] = field(default_factory=dict)
    new_candidates: dict[str, dict] = field(default_factory=dict)
    append_paths: dict[str, list[str]] = field(default_factory=dict)
    third_party: list[str] = field(default_factory=list)
    promote: list[tuple[str, str]] = field(default_factory=list)
    idle: list[str] = field(default_factory=list)
    loose: list[tuple[str, int]] = field(default_factory=list)
    unit_info: dict[str, tuple[int, int]] = field(default_factory=dict)

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
    owner: dict[str, str] = {}
    unmapped: list[str] = []
    for rel in iter_code_files(root):
        if registry.is_excluded(rel):
            continue
        try:
            match = registry.module_for_path(rel)
        except RegistryError:
            owner[rel] = ""
            continue
        if match is None:
            unmapped.append(rel)
        else:
            owner[rel] = match.module_id
    return owner, unmapped


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
    if not mid or module is None:
        return None
    prefix = parent.lower().split("/")
    children = 0
    for pattern in module.paths:
        parts = pattern.replace("\\", "/").lower().split("/")
        if len(parts) > len(prefix) and parts[:len(prefix)] == prefix and not _WILDCARD.search(parts[len(prefix)]):
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
        return None
    if resolved.known:
        module = registry.modules[resolved.id]
        return None if module.deprecated else resolved.id
    return resolved.id if resolved.candidate else None


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
              heat: Counter, recent: Counter) -> SyncPlan:
    plan = SyncPlan()
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
        body = {"paths": [path], "origin": "sync"}
        if len(files) >= MODULE_MIN_FILES and unit_heat > 0:
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
    for mid, module in sorted(registry.modules.items()):
        files = by_module.get(mid, [])
        if module.merged_into or module.deprecated or not files or memories.get(mid):
            continue
        if not any(recent.get(f, 0) for f in files):
            plan.idle.append(mid)
    return plan


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
    modules.update(copy.deepcopy(plan.new_modules))
    candidates.update(copy.deepcopy(plan.new_candidates))
    if candidates or "candidates" in out:
        out["candidates"] = candidates
    if plan.third_party:
        third = list(out.get("third_party") or [])
        third += [p for p in plan.third_party if p not in third]
        out["third_party"] = third
    return out


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
    return lines


def run_sync(root: Path, apply: bool) -> int:
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
    except RegistryError as exc:
        print(f"无法同步：{exc}")
        return 1
    storage = FilesStorage(config.root, detect_vcs(config.root, config.get("vcs")))
    memories = Counter(e.module for _, e in storage.iter_all() if e.status != "archived")
    _, (heat, recent) = file_heat_windows(config.root, HEAT_DAYS, IDLE_DAYS)
    plan = plan_sync(config.root, registry, memories, heat, recent)

    lines = render(plan)
    print("\n".join(lines) if lines else "modules.yaml 与代码目录一致，没有需要同步的内容")
    if not plan.changes:
        return 0
    lost = body_comments(body)
    if lost:
        print(f"注意：modules.yaml 中间有 {lost} 行注释会在重写时丢失（文件开头的注释保留），提交前请看一眼 diff")
    if not apply:
        print("以上为预览；确认后加 --apply 写入 modules.yaml（只追加，不改已有模块名）")
        return 0
    new_data = apply_plan(data, plan)
    try:
        ModuleRegistry(new_data)
    except RegistryError as exc:
        print(f"无法同步：{exc}")
        return 1
    path.write_text(dump_modules(header, new_data), encoding="utf-8", newline="\n")
    print("已写入 .memory/modules.yaml。运行 pmem doctor 检查覆盖率，然后提交 .memory/")
    return 0
