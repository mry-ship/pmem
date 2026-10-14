"""从 captures/ 挑选代表性样本，脱敏后写入 tests/fixtures/hook_payloads/，保留原始字节特征（BOM、乱码）。"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "tests" / "fixtures" / "hook_payloads"
REPO = str(HERE.parents[1])


def sanitize(raw: str) -> str:
    variants = {REPO, REPO.lower(), REPO[0].lower() + REPO[1:], REPO.replace("\\", "/")}
    for v in sorted(variants, key=len, reverse=True):
        raw = raw.replace(json.dumps(v)[1:-1], "C:\\\\work\\\\demo").replace(v, "C:/work/demo")
    raw = raw.replace("/c:/Users/ZhengLangPC/Desktop/Cursor-Project-Memory", "/c:/work/demo")
    raw = re.sub(r'"user_email":"[^"]*"', '"user_email":"dev@example.com"', raw)
    raw = re.sub(r'"transcript_path":"[^"]*"', '"transcript_path":"C:\\\\transcripts\\\\conv.jsonl"', raw)
    return raw.replace("ZhengLangPC", "dev")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    picked: dict[str, str] = {}
    for path in sorted(HERE.joinpath("captures").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        event, raw = record["event"], record["raw"]
        if "_" in event:
            continue
        tool = re.search(r'"tool_name":"([^"]+)"', raw)
        name = f"{event}_{tool.group(1)}" if tool else event
        if event == "afterFileEdit" and "playground.txt" in raw and "\\u" not in raw and "中文测试" in raw:
            picked["afterFileEdit_mangled"] = raw
            continue
        if len(raw) < 4000 and "playground" in raw or name not in picked:
            picked[name] = raw
    for name, raw in picked.items():
        (OUT / f"{name}.json").write_bytes(sanitize(raw).encode("utf-8"))
        print(name)


if __name__ == "__main__":
    main()
