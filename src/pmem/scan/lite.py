"""轻量扫描：列出代码目录、文件数与近期改动热度，供 Agent 划分模块；也给 doctor 算覆盖率。"""
from __future__ import annotations

import os
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pmem.vcs.base import VCS
from pmem.vcs.detect import detect_vcs

CODE_EXTS = {
    ".cs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ".py", ".go", ".java", ".kt", ".kts",
    ".swift", ".m", ".mm", ".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".rb", ".php", ".lua", ".dart",
    ".scala", ".gd", ".shader", ".hlsl", ".sql", ".proto",
}
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "obj", "bin", "build", "dist", "out",
    ".venv", "venv", "__pycache__", ".idea", ".vs", ".vscode", ".cursor", ".memory", "target", ".gradle",
    ".next", ".nuxt", "coverage", ".pytest_cache", ".ruff_cache",
    # Go / PHP 依赖、iOS 依赖与构建产物、.NET 测试结果、Python 安装目录
    "vendor", "Pods", "Carthage", "DerivedData", "TestResults", "site-packages",
}
SKIP_SUFFIXES = (".egg-info",)
# Unity 编辑器在工程根目录生成的目录：同级同时有 Assets 和 ProjectSettings 才算，
# 业务代码里的同名目录（如 Scripts/Logs 日志模块）照常扫描
UNITY_GENERATED = {"Library", "Temp", "Logs", "UserSettings"}
UNITY_MARKERS = {"Assets", "ProjectSettings"}


def skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".") or name.endswith(SKIP_SUFFIXES)


def kept_dirs(names: list[str]) -> list[str]:
    """os.walk 同一层的子目录里，去掉依赖、构建产物和 Unity 工程根下的生成目录。"""
    unity_root = UNITY_MARKERS.issubset(names)
    return [d for d in names if not skip_dir(d) and not (unity_root and d in UNITY_GENERATED)]
THIRD_PARTY_NAMES = re.compile(
    r"^(plugins?|third[-_ ]?party|3rd[-_ ]?party|vendors?|externals?|deps|sdks?|.*sdk|googlemobileads|firebase|"
    r"facebook.*|appsflyer|maxsdk|ironsource|applovin|spine.*|dotween|demigiant|textmesh ?pro|sirenix|odin.*|"
    r"unitask|newtonsoft.*|bugly|tapjoy|unityads|admob|adjust|bestHTTP|lean ?tween|i2|photon.*)$",
    re.IGNORECASE,
)
HEAT_DAYS = 180
BULK_COMMIT = 100


def iter_code_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = kept_dirs(dirnames)
        for name in filenames:
            if os.path.splitext(name)[1].lower() in CODE_EXTS:
                yield Path(dirpath, name).relative_to(root).as_posix()


def file_heat_windows(root: Path, *windows: int, vcs: VCS | None = None) -> tuple[str, list[Counter]]:
    """一次读取提交历史，分别统计近 N 天各文件的改动次数（排除超过 BULK_COMMIT 个文件的大提交）。
    vcs 不传时自动探测；已接入的项目应传按配置（config 的 vcs）建好的适配器。"""
    windows = windows or (HEAT_DAYS,)
    today = date.today()
    cutoffs = [(today - timedelta(days=days)).isoformat() for days in windows]
    vcs = vcs or detect_vcs(root)
    commits = vcs.commits_since(min(cutoffs))
    heats = [Counter() for _ in windows]
    for day, files in commits:
        if not 0 < len(files) <= BULK_COMMIT:
            continue
        for heat, cutoff in zip(heats, cutoffs):
            if day >= cutoff:
                heat.update(files)
    return vcs.name, heats


def file_heat(root: Path, days: int = HEAT_DAYS, vcs: VCS | None = None) -> tuple[str, Counter]:
    name, (heat,) = file_heat_windows(root, days, vcs=vcs)
    return name, heat


def summarize(root: Path, depth: int = 4) -> str:
    root = root.resolve()
    files = list(iter_code_files(root))
    vcs, heat = file_heat(root)
    counts: Counter = Counter()
    changes: Counter = Counter()
    for rel in files:
        parts = rel.split("/")[:-1]
        for i in range(1, min(len(parts), depth) + 1):
            key = "/".join(parts[:i])
            counts[key] += 1
            changes[key] += heat.get(rel, 0)
    third = sorted(d for d in counts if THIRD_PARTY_NAMES.match(d.rsplit("/", 1)[-1]))
    third_roots = [d for d in third if not any(d.startswith(t + "/") for t in third if t != d)]

    lines = [
        f"项目：{root}",
        f"版本控制：{vcs}；代码文件：{len(files)}；热度 = 近 {HEAT_DAYS} 天改动该目录文件的次数（排除超过 {BULK_COMMIT} 个文件的大提交）",
        "",
        "疑似第三方 / SDK 目录（建议放入 third_party）：",
    ]
    lines += [f"  {d}  ({counts[d]} 个代码文件)" for d in third_roots] or ["  （未发现）"]
    lines += ["", "目录概览（代码文件数 / 热度）："]
    shown = 0
    for key in sorted(counts):
        if any(key == t or key.startswith(t + "/") for t in third_roots) or counts[key] < 3:
            continue
        level = key.count("/")
        lines.append(f"  {'  ' * level}{key.rsplit('/', 1)[-1]}/  {counts[key]} / {changes[key]}    [{key}]")
        shown += 1
        if shown >= 400:
            lines.append("  ……（目录过多已截断，可用 --depth 调小）")
            break
    loose = [f for f in files if "/" not in f]
    if loose:
        lines.append(f"  （根目录散落代码文件 {len(loose)} 个）")
    return "\n".join(lines)


def run_scan(root: Path, depth: int) -> int:
    print(summarize(root, depth))
    return 0
