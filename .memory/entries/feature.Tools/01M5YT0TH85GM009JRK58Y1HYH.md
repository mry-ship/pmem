---
id: 01M5YT0TH85GM009JRK58Y1HYH
module: feature.Tools
entity: SeenDedupe
kind: correction
status: active
supersedes:
- 01M5YS60662VJFP6K0VFNQ8732
anchors:
- src/pmem/core/seen.py#note_handoff
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 交接文件已加锁；同模块同时查仍可能认错对话
verify: uv run pytest tests/test_quality_efficiency.py::test_parallel_handoffs_keep_every_conversation
applies: 解释对话内去重认错对话时；交接文件已加锁之后
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
更正：cli-handoff.json 的读改写已经加了跨进程锁，并行 note_handoff 不会互相盖掉。等锁超过 5 秒仍照常写，宁可偶尔丢一次，也不卡住开发。
仍成立：认领后不删交接；两个对话在 120 秒内查同一模块，仍可能认到对方的对话，后果只是少显示几条正文。
