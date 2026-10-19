"""代码文件与模块的对应：覆盖率（多少文件归到了模块、哪些目录没有归属、哪些路径互相重叠、哪些模块一个文件都没匹配到），
以及按模块汇总的改动热度。doctor、sync、seed、report 共用这一份映射规则。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import iter_code_files


@dataclass
class FileMapping:
    files: int = 0
    excluded: int = 0
    owner: dict[str, str] = field(default_factory=dict)
    conflicted: dict[str, str] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)


def map_files(root: Path, registry: ModuleRegistry) -> FileMapping:
    """代码文件 → 所属模块（含冷候选）；路径重叠的进 conflicted（文件 → 报错的第一句），第三方和忽略的只计数。"""
    mapping = FileMapping()
    for rel in iter_code_files(root):
        mapping.files += 1
        if registry.is_excluded(rel):
            mapping.excluded += 1
            continue
        try:
            match = registry.module_for_path(rel)
        except RegistryError as exc:
            mapping.conflicted[rel] = str(exc).split("，")[0]
            continue
        if match is None:
            mapping.unmapped.append(rel)
        else:
            mapping.owner[rel] = match.module_id
    return mapping


def module_heat(registry: ModuleRegistry, heat: Counter, include_candidates: bool = True) -> Counter:
    """文件改动次数按所属模块汇总；路径重叠、没有归属的文件不计。"""
    totals: Counter = Counter()
    for path, count in heat.items():
        try:
            match = registry.module_for_path(path)
        except RegistryError:
            continue
        if match is not None and (include_candidates or not match.candidate):
            totals[match.module_id] += count
    return totals


def coverage_report(root: Path, registry: ModuleRegistry) -> dict:
    mapping = map_files(root, registry)
    unmapped = Counter("/".join(rel.split("/")[:3]) if "/" in rel else "（根目录）" for rel in mapping.unmapped)
    used = Counter(mapping.owner.values())
    shells = [
        mid for mid, m in {**registry.modules, **registry.candidates}.items()
        if m.paths and not m.merged_into and used[mid] == 0
    ]
    total = mapping.files - mapping.excluded
    return {
        "files": mapping.files,
        "excluded": mapping.excluded,
        "mapped": len(mapping.owner),
        "coverage": len(mapping.owner) / total if total else 1.0,
        "unmapped": unmapped.most_common(10),
        "conflicts": sorted(set(mapping.conflicted.values()))[:10],
        "shells": shells,
    }
