---
id: 01M640H7ZXJVBR6010GSBKVABQ
module: feature.Gate
entity: FeatureReminder
kind: feature
status: active
supersedes:
- 01M640HJZ6NA9ZEH1TPDJY424G
anchors:
- src/pmem/hooks/reminders.py#_written
- src/pmem/hooks/reminders.py#_modules_of_recorded_ids
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: written 损坏时凭本对话 recorded id 认出模块，不重复催写
verify: uv run pytest tests/hooks/test_gate.py -k recorded_ids_exist_but_written_cleared
applies: 回合结束判断本对话是否已写过该模块时
aliases:
- 催写去重
- 重复催
---
需求来源：2026-10-29 FixOrder：催写未转化里约一半是长对话再催已经写过的模块；按本对话已写入认出模块，不要重复催。
必须保持：结束提醒判断「本对话写过」时，除 written 与 cli_recorded 外，还用 recorded 里的记忆 id 到 .memory/entries/*/id.md 找回模块。
written 被重置后，文件还在就不该再催该模块。
id 含路径分隔符则跳过，避免当文件名。
文件找不到仍催。
仍不区分 kind：只写了教训也算写过（见同议题风险 01M5CAVJFYT5C7R57JGAQ2S0MZ）。
入口：src/pmem/hooks/reminders.py _written、_modules_of_recorded_ids。
不替代「每个改过的模块要功能记录」的既有功能（01M5CAVH8YBS1P63AJ88KJNTRG）。
