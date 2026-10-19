"""模块覆盖率：代码文件有多少归到了模块、哪些目录没有归属、哪些路径互相重叠、哪些模块的路径一个文件都没匹配到。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import iter_code_files


def coverage_report(root: Path, registry: ModuleRegistry) -> dict:
    files = list(iter_code_files(root))
    mapped = excluded = 0
    unmapped: Counter = Counter()
    conflicts: set[str] = set()
    used: Counter = Counter()
    for rel in files:
        if registry.is_excluded(rel):
            excluded += 1
            continue
        try:
            match = registry.module_for_path(rel)
        except RegistryError as exc:
            conflicts.add(str(exc).split("，")[0])
            continue
        if match is None:
            unmapped["/".join(rel.split("/")[:3]) if "/" in rel else "（根目录）"] += 1
        else:
            mapped += 1
            used[match.module_id] += 1
    shells = [
        mid for mid, m in {**registry.modules, **registry.candidates}.items()
        if m.paths and not m.merged_into and used[mid] == 0
    ]
    total = len(files) - excluded
    return {
        "files": len(files),
        "excluded": excluded,
        "mapped": mapped,
        "coverage": mapped / total if total else 1.0,
        "unmapped": unmapped.most_common(10),
        "conflicts": sorted(conflicts)[:10],
        "shells": shells,
    }
