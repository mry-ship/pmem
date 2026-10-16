---
id: 01M4XF76H4M7K82C5X5KXNM9JB
module: feature.Gate
entity: AutoAnchors
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
revision: git:a0936e7
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-15'
---
结论：写记忆时，闸门会按本对话改过的文件自动补 anchors。

做法：
- afterFileEdit 时按“模块|相对路径”记下改过的文件；
- record_memory 的 preToolUse 中，如果 Agent 没填 anchors，用 updated_input 补上该模块最近改过的最多 5 个文件；
- Agent 自己填了 anchors 就不覆盖。

目的：实测大多数记忆没有 anchors，于是代码变化后无法标记 stale，按文件路径检索时也无法加分。

风险：MCP 调用时 Cursor 是否真的采用 preToolUse 的 updated_input，尚未在真实对话中验证（source_conversation 注入同样待验证）。
验证方法：在真实对话里改一个文件后用 MCP 写记忆，查看生成的 .md 是否带 anchors。

另外，终端里执行的 pmem record 现在会在 Hook 侧记 record_call 事件（带对话 id）。这样 Agent 用 PMEM_NO_EVENTS=1 跑 CLI 时，收益报告里的“提醒后写了”也能统计到。
