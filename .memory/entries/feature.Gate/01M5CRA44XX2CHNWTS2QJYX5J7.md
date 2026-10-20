---
id: 01M5CRA44XX2CHNWTS2QJYX5J7
module: feature.Gate
entity: InCommandSearch
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#Gate.on_pre_tool
- src/pmem/hooks/shell.py#writes_before_search
- src/pmem/hooks/payload.py
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 同一条命令里只有检索之后的写入才放行；EditNotebook 的目标也要拦
verify: uv run pytest tests/hooks/test_gate.py -k "same_command or write_before_search"
aliases:
- 先写后查
- 同一条命令检索
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，复查发现闸门可被“先写后查”绕过。
必须保持：
1) 一条终端命令里既有 pmem search/graph 又有写入时，只有写在第一处检索之后、且属于被检索模块的写入先放行；检索之前的写入（Set-Content x; pmem search ...）照常检查。原先不分前后一律放行。
2) EditNotebook 的 target_notebook、以及 target_file 在 Hook 输入损坏走正则兄底时也能取到，按写入工具拦截。
入口：gate.py 的 on_pre_tool（Shell 分支）、shell.writes_before_search、payload._INPUT_FIELDS。
