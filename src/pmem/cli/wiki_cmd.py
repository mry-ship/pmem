"""pmem wiki：从记忆文件生成可浏览的模块 Wiki（Markdown）。写入记忆后也会自动重新生成（wiki.auto）。"""
from __future__ import annotations

from pathlib import Path

from pmem.generate.wiki import MARKER, write_wiki

__all__ = ["MARKER", "run_wiki"]


def run_wiki(root: Path, out: str | None) -> int:
    from pmem.service import MemoryService

    service = MemoryService(root)
    try:
        result = write_wiki(service, root / (out or str(service.config.get("wiki.dir"))))
    finally:
        service.close()
    print(f"Wiki 共 {result.pages} 页（更新 {result.written}、删除 {result.removed}）：{result.index}")
    if result.skipped:
        print(f"跳过 {len(result.skipped)} 个同名但不是 pmem 生成的页面（未覆盖）：{'、'.join(result.skipped[:10])}；"
              "换一个输出目录再生成")
        return 1
    return 0
