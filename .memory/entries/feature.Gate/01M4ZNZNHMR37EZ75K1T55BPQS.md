---
id: 01M4ZNZNHMR37EZ75K1T55BPQS
module: feature.Gate
entity: AutoAnchors
kind: conclusion
status: active
supersedes:
- 01M4XF76H4M7K82C5X5KXNM9JB
anchors:
- src/pmem/hooks/gate.py
revision: git:7a9926b
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 自动补参
- updated_input
- 注入参数
verified: '2026-10-19'
---
结论：Cursor 3.9 对 MCP 调用会采用 preToolUse 返回的 updated_input，所以闸门自动补的参数确实会送到记忆服务。

写记忆时的自动补参：
- afterFileEdit 时按“模块|相对路径”记下本对话改过的文件；
- record_memory 的 preToolUse 中，Agent 没填 anchors 就用 updated_input 补上该模块最近改过的最多 5 个文件，Agent 自己填了就不覆盖；
- 同模块且同议题写过草稿时补 draft_id。
目的是让记忆带上关联代码：实测大多数记忆没写 anchors，代码变了就无法标 stale，按文件路径检索也无法加分。

证据：spike 录下的 Hook 载荷里，23 次 search_memory 调用在 preToolUse 时没有 source_conversation，到同一次调用的 beforeMCPExecution 时已带上闸门注入的值，服务端全部返回成功。
record_memory 补 draft_id/anchors 走的是同一机制，但还没在真实对话里直接看到生成的 .md 带 anchors（需要在 Cursor 里启用项目的 pmem MCP 后验证）。

由此发现的问题（已修）：Cursor 的 preToolUse 里 tool_name 只有 "MCP:search_memory"，不带服务名，闸门原先会把 source_conversation 注入别家记忆服务的同名工具（如 tilematch-dev-memory）。
TileMatch 那边容忍了多出的参数，参数校验严格的服务可能直接拒绝调用。
现在 search_memory 只有在工具名含 pmem（Claude/Codex 的工具名带服务名），或 module/path 能在 pmem 注册表里解析时才注入；
不带模块的全局检索不再注入，代价是收益报告里这类检索少了对话归属。
