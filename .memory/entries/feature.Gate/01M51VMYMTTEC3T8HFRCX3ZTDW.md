---
id: 01M51VMYMTTEC3T8HFRCX3ZTDW
module: feature.Gate
entity: GateDefaults
kind: decision
status: active
supersedes:
- 01M51P2FW5SRCZRHV2W02NGE0J
anchors:
- src/pmem/hooks/gate.py#on_stop
- src/pmem/hooks/gate.py#on_after_mcp
- src/pmem/hooks/gate.py#memory_count
- src/pmem/hooks/gate.py#cli_args
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 无需记录
- 自动写记忆
- 结束提醒
- 已查过
- 放行
- Out-Null
---
决定：闸门默认用强制模式（gate.mode: block）；结束提醒默认也覆盖“整个对话只查了记忆”的情况（gate.analysis_reminder: true）。记忆由 Agent 自动写，不再提供“回复无需记录”的出口。

依据：
- 本仓库的开发对话里，改代码共涉及 10 个“对话×模块”，只有 1 个是 Agent 主动先查的；warn 档只拦一次，规则文件本身几乎约束不了“先查再改”。
- 结束提醒原先允许回复“无需记录”，Agent 曾把真实的设计决定判成“机械改动”而跳过。用户要求自动写记忆。

现行做法：
- 改了模块却没写记忆：stop 的 followup 要求 Agent 直接为每个模块写一条，不要询问用户。
- 只查了记忆：有新结论就写，没有就说明“已核对，无新结论”。

强制模式下怎样算“查过”（2026-10-16 收紧，推翻了原先“尝试过检索就放行，成败不论”）：
- MCP 检索在返回 ok: true 之后才登记（Cursor 的 afterMCPExecution，Claude Code、Codex 的 PostToolUse）；preToolUse、beforeMCPExecution 不再登记，调用失败也不算。日志核对过：Cursor 下 18 次 MCP 检索的 afterMCPExecution 全部送达并解析成功，不会因此卡死。
- 终端 pmem search/graph --module 仍在执行前登记（同一条命令里先查再写要能放行），但输出被丢弃（> $null、*> 文件、| Out-Null/Out-File/Set-Content）时不算，因为 Agent 并没有看到记忆。
- 只算现行记忆：模块里的记忆全部被替代或停用时不再拦截，拦截提示里的条数也只算现行的。
- 查了哪个模块只放行哪个模块。MCP 不可用时的出口仍是终端 pmem search，以及让用户说“跳过记忆”。

风险：提醒可能引出应付式记忆，需要在 pmem report 里观察“提醒后写下”的记忆质量。
