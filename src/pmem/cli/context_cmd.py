"""pmem context：改前上下文（harness 实验）。--refresh 重算缓存（后台进程调用），带路径时列出该文件的提示。"""
from __future__ import annotations

import json
from pathlib import Path

from pmem import context
from pmem.core.config import Config
from pmem.vcs.detect import detect_vcs


def settings(config: Config) -> tuple[int, int, float]:
    return (int(config.get("harness.window_days")), int(config.get("harness.min_pair")),
        float(config.get("harness.min_ratio")))


def run_context(root: Path, path: str | None, refresh: bool, as_json: bool) -> int:
    config = Config.load(root)
    cache_dir = config.cache_dir
    window, min_pair, min_ratio = settings(config)
    if refresh:
        vcs = detect_vcs(config.root, config.get("vcs"))
        data = context.refresh(cache_dir, vcs, window, min_pair, min_ratio)
        if data is None:
            print("已有后台进程在重算，跳过")
            return 0
        print(f"已重算：读到 {data['commits']} 次提交（{data['vcs']}，近 {window} 天），{len(data['files'])} 个文件有提示")
        return 0
    data = context.load(cache_dir)
    if data is None:
        print("还没有缓存：先运行 pmem context --refresh（接入后开了 harness.mode，新对话开始时也会在后台算）")
        return 1
    if not path:
        print(f"缓存：{data['commits']} 次提交（{data['vcs']}，近 {data['window']} 天），{len(data['files'])} 个文件有提示")
        return 0
    rel = Path(path)
    if rel.is_absolute():
        try:
            rel = rel.resolve().relative_to(config.root)
        except ValueError:
            pass
    key = rel.as_posix()
    hints = context.lookup(data, key, max_files=int(config.get("harness.max_files")))
    if as_json:
        print(json.dumps({"file": key, **{k: [list(x) for x in v] for k, v in hints.items()}}, ensure_ascii=False, indent=2))
        return 0
    text = context.render(key, hints, config.root)
    print(text or f"{key}：没有可提示的历史（没有常一起改的文件，也没有近期修复提交）")
    return 0
