"""pmem map：生成记忆演化图（本地 HTML）并打印图上自检的总评。"""
from __future__ import annotations

import json
from pathlib import Path

from pmem.core.config import Config
from pmem.generate.memmap import MAP_FILE, write_map_html
from pmem.metrics.memmap import build_memmap, render_summary


def run_map(root: Path, out: str | None, days: int, as_json: bool) -> int:
    model = build_memmap(root, days)
    if as_json:
        print(json.dumps(model, ensure_ascii=False, indent=2))
        return 0
    target = root / out if out else root / str(Config.load(root).get("wiki.dir")) / MAP_FILE
    path = write_map_html(model, target)
    print(render_summary(model))
    print(f"\n记忆图已生成：{path}（浏览器打开；滚轮缩放、拖动平移、点节点看全文、点自检项定位）")
    return 0
