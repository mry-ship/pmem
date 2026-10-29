---
id: 01M640HJZ6NA9ZEH1TPDJY424G
module: feature.Gate
entity: RecordedWritten
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#_written
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: recorded 里的记忆 id 能对上文件时，该模块算本对话已写过
verify: uv run pytest tests/hooks/test_gate.py -k recorded_ids_exist
applies: written 损坏被重置但 recorded 仍有本对话写入 id
---
用户要求：本对话已经写过记忆的模块，结束时不要再催写。

必须保持：判断写过时，除 written 字典和 cli_recorded 外，还用 recorded 里的记忆 id 对照 .memory/entries/<模块>/<id>.md 认出模块。
找不到文件的 id 不算写过。
只写了教训也算写过，不再提醒补功能记录。

适用：written 损坏或类型不对被重置成空字典，但 recorded 仍留下本对话写入 id 时。

入口：src/pmem/hooks/reminders.py#_written
