"""pmem map：生成记忆演化图（本地 HTML）并打印图上自检的总评。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pmem.core.config import Config
from pmem.generate.memmap import MAP_FILE, write_map_html
from pmem.generate.wiki import project_wiki_dir
from pmem.metrics.memmap import build_memmap, render_summary


def run_map(root: Path, out: str | None, days: int, as_json: bool) -> int:
    model = build_memmap(root, days)
    if as_json:
        print(json.dumps(model, ensure_ascii=False, indent=2))
        return 0
    if out:
        target = root / out
    else:
        folder = project_wiki_dir(root, str(Config.load(root).get("wiki.dir")))
        if folder is None:
            print("wiki.dir 指向了项目目录以外，已拒绝生成", file=sys.stderr)
            return 2
        target = folder / MAP_FILE
    path = write_map_html(model, target)
    print(render_summary(model))
    print(f"\n记忆图已生成：{path}（浏览器打开；滚轮缩放、拖动平移、点节点看全文、点自检项定位）")
    return 0
