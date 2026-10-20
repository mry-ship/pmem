---
id: 01M5CVKGEEVA17GR6P007VA4YM
module: feature.Gate
entity: InCommandSearch
kind: feature
status: active
supersedes:
- 01M5CRA44XX2CHNWTS2QJYX5J7
anchors:
- src/pmem/hooks/shell.py#searched_before_writes
- src/pmem/hooks/mcp.py#McpCalls._confirm_cli_calls
- src/pmem/hooks/gate.py#Gate.on_pre_tool
- src/pmem/hooks/review.py#Review._search_digest
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 命令内检索只放行按顺序接在该模块检索后的写入；检索失败时事后提醒补查
verify: uv run pytest tests/hooks/test_gate.py -k "in_command or failed_in_command
  or same_command"
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求两轮复查后全部修复。
必须保持：
1) 一条终端命令里有 pmem search/graph 又有写入时，只有写在「该文件所属模块」的检索之后、且中间只隔着 &&、; 或换行的写入先放行；
   先写后查、查的是别的模块、隔着 ||（检索失败才执行）或 &（并行）的照常检查。
   语句超过 40 条时不豁免。
2) 检索用 ; 串联却执行失败（输出里看不到模块名）、而命令已经改了该模块文件时，post-tool 立即用 additional_context 提醒补查（事件 search_failed_after_write）。
   PowerShell 5 没有 &&，所以 ; 不能不认。
3) EditNotebook 的 target_notebook、载荷损坏时 file_paths 列表都能取到。
4) 搜索命中多个模块时只给前 2 个摘要，没给的不记为已看过。会话状态锁可重入。
入口：gate.py on_pre_tool、shell.searched_before_writes、mcp._confirm_cli_calls、review._search_digest。
