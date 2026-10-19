"""把已有记忆里过长的正文行断开（按句号、分号和行内编号），方便直接打开文件阅读。只改换行和缩进，不改文字。"""
from __future__ import annotations

from pathlib import Path

from pmem.core.config import Config
from pmem.core.fileio import write_atomic
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.core.textfmt import format_content
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

PREVIEW_LINES = 8


def run_format(root: Path, module: str | None, apply: bool) -> int:
    config = Config.load(root)
    if module:
        registry = ModuleRegistry.load(config.modules_path) if config.modules_path.exists() else ModuleRegistry({})
        try:
            module = registry.resolve_module(module).id
        except RegistryError as exc:
            print(exc)
            return 1
    storage = FilesStorage(root, detect_vcs(root, config.get("vcs")))
    scanned = changed = 0
    sample: list[str] = []
    for path, entry in storage.iter_all():
        if module and entry.module != module:
            continue
        scanned += 1
        formatted = format_content(entry.content)
        if formatted == entry.content:
            continue
        changed += 1
        if not sample:
            sample = [f"  {entry.module}/{entry.entity} {entry.id} 整理后："]
            sample += [f"    {line}" for line in formatted.splitlines()[:PREVIEW_LINES]]
        if apply:
            entry.content = formatted
            write_atomic(path, entry.to_markdown())
    print(f"检查记忆 {scanned} 条，其中 {changed} 条有过长的行需要断开。")
    if sample:
        print("\n".join(sample))
    if changed and not apply:
        print("以上为预览；确认无误后加 --apply 写回记忆文件，再提交 .memory/。")
    elif apply:
        print(f"已整理 {changed} 条记忆。")
    return 0
