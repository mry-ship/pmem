"""校准引用判定阈值：打印每条记忆与各对话记录的字面重合得分。

用法：uv run python scripts/calibrate_cite.py <项目根> <transcript.jsonl>...
无关项目的对话记录给出噪声底线，明确用到记忆的对话给出正样本。
"""
from __future__ import annotations

import sys
from pathlib import Path

from pmem.metrics.cite import assistant_text, judge
from pmem.service import MemoryService


def main() -> None:
    service = MemoryService(sys.argv[1])
    memories = {e.id: e.content for e in service.index.entries()}
    labels = {e.id: f"{e.module}/{e.entity}" for e in service.index.entries()}
    for raw in sys.argv[2:]:
        reply = assistant_text(Path(raw))
        print(f"\n== {Path(raw).name}  回复 {len(reply)} 字")
        scores = judge(memories, reply)
        for mid, info in sorted(scores.items(), key=lambda kv: -kv[1]["score"]):
            print(f"  {labels[mid]:<32} score={info['score']:.3f} {'CITED' if info['cited'] else ''}")


if __name__ == "__main__":
    main()
