---
id: 01M521A1KW9ME0PK117CGGB5MW
module: feature.Gate
entity: AutoAnchors
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_inject
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 自动补锚点
- 覆盖草稿
verified: '2026-10-19'
---
决定：闸门给 record_memory 补参数时，如果这次会覆盖草稿（Agent 自带 draft_id，或闸门按“同模块同议题”注入了本对话的草稿 id），就不再按本对话改过的文件自动补 anchors，交给记忆服务沿用草稿原有的锚点。

原因：记忆服务改为覆盖时没传的列表沿用原值；闸门若照旧补锚点，会把草稿里手写的“路径#函数名”锚点换成只到文件的锚点，以后该文件任何改动都会让记忆标为需核实。

风险：草稿写下之后本对话又改了别的文件时，新文件不会自动加入锚点，需要 Agent 显式传 anchors。
