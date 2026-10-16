---
id: 01M4X7MV5T0RF0ZQYDDGJ1J768
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
revision: git:92be39d
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
根因：一条终端命令里用 ; / && / | 串了多个 `pmem record`（或 `pmem search`）时，闸门只认第一个，后面几个模块的写入/检索都没登记，结束时会对已经记过的模块误发“还没有写研发记忆”提醒（检索同理，会多拦一次）。

现象：一条 PowerShell 命令依次 record 了 feature.Retrieval、infra.Model、feature.Import，stop 仍提醒 infra.Model 未记录。

处理：解析终端命令时按分隔符拆段，收集每一段的 pmem search/record 参数，逐个登记。

排查同类误报时：先看 Agent 当轮执行的终端命令是否把多个 pmem 调用写在一行，以及调用前是否发生过 preCompact（压缩会清空 searched/warned，但不清空 cli_recorded）。
