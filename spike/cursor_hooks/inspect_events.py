"""查看指定事件最近一次录制的字段（长字符串截断），并抽样对话记录格式。仅用于实测。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CAPTURES = Path(__file__).resolve().parent / "captures"


def show(event: str) -> str | None:
    files = sorted(CAPTURES.glob(f"*_{event}.json"))
    print(f"== {event}: {len(files)} 份")
    if not files:
        return None
    raw = json.loads(files[-1].read_text(encoding="utf-8"))["raw"].lstrip("\ufeff")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("   （JSON 损坏）", raw[:300])
        return None
    for key, value in data.items():
        text = json.dumps(value, ensure_ascii=False)
        print(f"   {key}: {text[:160]}")
    return data.get("transcript_path")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    transcript = None
    for event in sys.argv[1:]:
        transcript = show(event) or transcript
    if transcript and Path(transcript).exists():
        lines = Path(transcript).read_text(encoding="utf-8").splitlines()
        print(f"== transcript: {len(lines)} 行")
        for line in lines[-6:]:
            item = json.loads(line)
            summary = {k: (v if not isinstance(v, (str, list, dict)) else json.dumps(v, ensure_ascii=False)[:200])
                       for k, v in item.items()}
            print("  ", summary)


if __name__ == "__main__":
    main()
