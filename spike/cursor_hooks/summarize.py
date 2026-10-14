"""汇总 captures/ 下的录制结果，仅用于 M0 实测。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parent / "captures"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    since = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for path in sorted(CAPTURE_DIR.glob("*.json")):
        if int(path.name.split("_", 1)[0]) < since:
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        raw = record["raw"]
        print(f"===== {path.name} cwd={record['cwd']} bom={raw.startswith(chr(0xFEFF))}")
        try:
            data = json.loads(raw.lstrip("\ufeff") or "{}")
        except json.JSONDecodeError:
            print("  RAW", raw[:400])
            continue
        for key, value in data.items():
            print(f"   {key}: {json.dumps(value, ensure_ascii=False)[:300]}")


if __name__ == "__main__":
    main()
