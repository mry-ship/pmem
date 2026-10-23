"""pmem spec：模块规格的骨架、目录和完成情况。正文由 pmem-spec 技能写。"""
from __future__ import annotations

import sys
from pathlib import Path

from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.generate.spec import format_list, incomplete, index_specs, init_specs, project_spec_dir

__all__ = ["ensure_spec_skeletons", "run_spec"]


def ensure_spec_skeletons(root: Path) -> tuple[int, str]:
    """给已登记模块补还没有的规格骨架。正文不在这里写。"""
    config = Config.load(root)
    if not config.modules_path.exists():
        return 0, "还没有模块名单，规格等划分模块后再补"
    target = project_spec_dir(root, str(config.get("spec.dir") or ""))
    if target is None:
        return 2, "spec.dir 指向了项目目录以外，规格骨架未写"
    try:
        registry = ModuleRegistry.load(config.modules_path)
    except RegistryError as exc:
        return 2, f"模块名单读不了，规格骨架未写：{exc}"
    if not any(not module.merged_into for module in registry.modules.values()):
        return 0, "还没有已登记模块，规格目录等划分模块后再补"
    result = init_specs(registry, target)
    if result.blocked:
        return 2, f"有 {len(result.blocked)} 个模块不能写成规格文件：{'、'.join(result.blocked[:10])}"
    return 0, f"规格骨架：新写 {result.written}，已有 {result.skipped}，目录 {target}"


def run_spec(root: Path, action: str | None, check: bool) -> int:
    config = Config.load(root)
    target = project_spec_dir(root, str(config.get("spec.dir") or ""))
    if target is None:
        print("spec.dir 指向了项目目录以外，已拒绝", file=sys.stderr)
        return 2
    try:
        registry = ModuleRegistry.load(config.modules_path)
    except RegistryError as exc:
        print(f"模块名单读不了：{exc}", file=sys.stderr)
        return 2
    if action == "init":
        code, message = ensure_spec_skeletons(root)
        print(message, file=sys.stderr if code else sys.stdout)
        return code
    if action == "fill":
        code, message = ensure_spec_skeletons(root)
        if code:
            print(message, file=sys.stderr)
            return code
        if not message.startswith("规格骨架"):
            print(message)
            return 0
        index_specs(registry, target)
        missing = incomplete(registry, target)
        print(message)
        if not missing:
            print("规格首稿都已写完。")
            return 0
        print("这些模块的四份正文还没写全：" + "、".join(missing))
        print("本命令只铺骨架、不写正文。按 pmem-spec 把上面每个模块按代码写全："
              "程序和现状写到能重做；策划和美术只写看得到的，看不到的写「尚未写入」并留空。一句一行。")
        return 1
    if action == "index":
        result = index_specs(registry, target)
        if result.blocked:
            print(f"有 {len(result.blocked)} 个模块不能写成规格文件：{'、'.join(result.blocked[:10])}",
                  file=sys.stderr)
            return 2
        print(f"规格目录已更新：{result.index}")
        return 0
    print(format_list(registry, target))
    if check and incomplete(registry, target):
        return 1
    return 0
