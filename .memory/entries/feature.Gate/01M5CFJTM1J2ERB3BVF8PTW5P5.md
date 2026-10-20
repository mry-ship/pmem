---
id: 01M5CFJTM1J2ERB3BVF8PTW5P5
module: feature.Gate
entity: AutoAnchors
kind: conclusion
status: active
supersedes:
- 01M4ZNZNHMR37EZ75K1T55BPQS
anchors:
- src/pmem/hooks/mcp.py#_inject
- src/pmem/hooks/gate.py#on_pre_tool
- src/pmem/hooks/mcp.py#_draft_open
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Cursor 采用 preToolUse 的 updated_input；record 自动补锚点有前提
aliases:
- 自动补参
- updated_input
- 注入参数
---
结论：Cursor 3.9 对 MCP 调用会采用 preToolUse 返回的 updated_input，闸门自动补的参数确实送到记忆服务（spike 载荷里 23 次 search_memory 在 beforeMCPExecution 时都已带上注入的 source_conversation，服务端全部成功）。
写记忆时的自动补参：afterFileEdit 按“模块|相对路径”记下本对话改过的文件；record_memory 的 preToolUse 里 Agent 没填 anchors 就补上该模块最近改过的最多 5 个文件，自己填了不覆盖。
更正（多了前提）：本次已带 draft_id（传入或注入的），或载荷被转码损坏时，都不补锚点；同模块同议题的草稿还没提交时才自动补 draft_id。
search_memory 只在工具名含 pmem（Claude/Codex 的工具名带服务名），或 module/path 能在 pmem 注册表里解析时才注入；
Cursor 的 tool_name 只有 "MCP:search_memory"，原先会注入别家同名工具。
不带模块的全局检索不注入，代价是收益报告里这类检索少了对话归属。
