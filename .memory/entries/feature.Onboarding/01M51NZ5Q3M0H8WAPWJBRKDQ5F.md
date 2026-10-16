---
id: 01M51NZ5Q3M0H8WAPWJBRKDQ5F
module: feature.Onboarding
entity: Hooks
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/cli/doctor_cmd.py
revision: git:6d89f59
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- postToolUse
- matcher
- 重新init
---
决定：pmem init 给 Cursor 生成的 postToolUse Hook 带 matcher "Read"，Claude Code 的 PostToolUse matcher 也加上 Read，只在读文件后触发记忆摘要。

原因：postToolUse 每次工具调用都会触发，不加 matcher 就会每次启动一个 pmem 进程，拖慢所有工具调用。已在 Cursor（Windows）实测：加上 matcher 后，读文件时摘要照样送达 Agent。

升级提示：老项目的 hooks.json 没有这一项。pmem doctor 发现缺少 "pmem hook post-tool" 时会警告“读代码时的记忆摘要未接入”，并提示重新运行 pmem init。规则模板同时加了两条：回答模块相关问题前先 search_memory；想看模块全貌用 memory_graph。“何时写”还加了一条：到了时机直接写，不问用户、不等提醒，改过的模块结束前每个写一条。已接入的项目要重新运行 pmem init，规则才会更新。
