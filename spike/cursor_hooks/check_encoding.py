"""检查最近录制的 afterFileEdit 各变体能否被正确解析出中文，仅用于 M0 实测。"""
from __future__ import annotations

import json
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parent / "captures"
EXPECTED = "中文测试：汇总记忆，引号\"和反斜杠\\结尾。"
OUT = CAPTURE_DIR / "encoding_report.txt"


def try_parse(raw: str) -> tuple[str, str]:
    text = raw.lstrip("\ufeff")
    try:
        return "utf8", json.loads(text)["edits"][0]["new_string"]
    except Exception as exc:  # noqa: BLE001
        first = repr(exc)[:80]
    try:
        fixed = text.encode("gbk", errors="replace").decode("utf-8", errors="replace")
        return "gbk_roundtrip", json.loads(fixed)["edits"][0]["new_string"]
    except Exception as exc:  # noqa: BLE001
        return "fail", f"{first} / {exc!r}"[:200]


def main() -> None:
    lines = []
    for path in sorted(CAPTURE_DIR.glob("*_afterFileEdit*.json"))[-8:]:
        record = json.loads(path.read_text(encoding="utf-8"))
        if "playground" not in record["raw"]:
            continue
        how, value = try_parse(record["raw"])
        lines.append(f"{path.name}\thow={how}\tok={value.strip() == EXPECTED}\tvalue={value!r}")
    OUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
