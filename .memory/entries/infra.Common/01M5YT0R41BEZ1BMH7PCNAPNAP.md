---
id: 01M5YT0R41BEZ1BMH7PCNAPNAP
module: infra.Common
entity: SeenHandoff
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/seen.py#note_handoff
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 交接文件写入加锁，并行登记不会丢掉对话
verify: uv run pytest tests/test_quality_efficiency.py::test_parallel_handoffs_keep_every_conversation
applies: Hook 在终端命令执行前登记 cli-handoff.json 时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
需求来源：并行的终端检索各自整份替换交接文件，后写的会盖掉先写的，命令行可能认领到别的对话，把正文折进错误的去重文件。
必须保持：note_handoff 在跨进程锁里读改写 cli-handoff.json。等锁最多 5 秒，超时仍写，不卡住 Hook。认领仍不删除交接；120 秒内两个对话查同一模块仍可能认错，只是不再因为丢更新而认错。
适用：同一项目里并行跑终端 pmem search 时。
