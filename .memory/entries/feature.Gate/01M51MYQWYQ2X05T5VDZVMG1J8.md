---
id: 01M51MYQWYQ2X05T5VDZVMG1J8
module: feature.Gate
entity: PromptReview
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#on_prompt
- src/pmem/generate/templates.py
revision: git:a0fc859
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 提问时注入
- 每次提问查记忆
- additional_context
---
结论：在 Cursor 里，没有一个 Hook 既在每次提问时触发、又能给这一轮注入上下文，所以“每次提问自动审查记忆”不能靠提问 Hook 直接塞记忆实现。

依据（Cursor 官方 Hooks 文档 cursor.com/docs/hooks）：
- beforeSubmitPrompt：每次提问都触发，但输出只有 continue / user_message，只能放行或拦截，不能注入内容；而且 Windows 中文系统下 prompt 字段常被 GBK 误解码。
- sessionStart：可返回 additional_context（加入对话初始系统上下文）和 env，但只在新建对话时触发一次，且即发即弃。
- postToolUse / postToolUseFailure：每次工具调用后触发，可返回 additional_context（追加在工具结果后），MCP 工具还可用 updated_mcp_tool_output 替换输出。
- afterShellExecution / afterMCPExecution：文档没有列出可影响上下文的输出字段。
- stop：followup_message 作为下一条用户消息自动提交，受 loop_limit 限制（默认 5，pmem 设 1）。
Claude Code 的 UserPromptSubmit 可以每次提问返回 additionalContext，与 Cursor 不同。

可行做法：提问时用 beforeSubmitPrompt 只记下问题；
读代码时用 postToolUse 注入该模块的记忆摘要，或像改代码那样拦一次；
回合结束时用 stop 核对“问题涉及模块却没查记忆”，再用 followup_message 补查一轮。
问题原文以 transcript_path 指向的 UTF-8 对话记录为准，不依赖可能乱码的 prompt 字段。
尚未在 Cursor 中实测 postToolUse 的 additional_context。
