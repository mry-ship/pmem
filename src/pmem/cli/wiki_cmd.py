"""pmem wiki：从记忆文件生成可浏览的模块 Wiki（Markdown）。写入记忆后也会自动重新生成（wiki.auto）。"""
from __future__ import annotations

import sys
from pathlib import Path

from pmem.generate.wiki import MARKER, project_wiki_dir, write_wiki

__all__ = ["MARKER", "run_wiki"]


def run_wiki(root: Path, out: str | None) -> int:
    from pmem.service import MemoryService

    target = root / (out or "")
    if out and target.exists() and not target.is_dir():
        print(f"--out 应是目录，{target} 是一个文件", file=sys.stderr)
        return 2
    service = MemoryService(root)
    try:
        if out:
            target = root / out
        else:
            target = project_wiki_dir(root, str(service.config.get("wiki.dir")))
            if target is None:
                print("wiki.dir 指向了项目目录以外，已拒绝生成", file=sys.stderr)
                return 2
        result = write_wiki(service, target)
    finally:
        service.close()
    print(f"Wiki 共 {result.pages} 页（更新 {result.written}、删除 {result.removed}）：{result.index}")
    if result.skipped:
        print(f"跳过 {len(result.skipped)} 个同名但不是 pmem 生成的页面（未覆盖）：{'、'.join(result.skipped[:10])}；"
              "换一个输出目录再生成")
        return 1
    if result.blocked:
        print(f"跳过 {len(result.blocked)} 个不能当文件名的模块（未写出）：{'、'.join(result.blocked[:10])}",
              file=sys.stderr)
    return 0
