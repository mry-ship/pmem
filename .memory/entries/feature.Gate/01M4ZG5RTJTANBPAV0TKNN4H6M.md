---
id: 01M4ZG5RTJTANBPAV0TKNN4H6M
module: feature.Gate
entity: DraftOverwrite
kind: conclusion
status: active
supersedes:
- 01M4Z9R2MF226TQJSCJJ2YG4YM
anchors:
- src/pmem/hooks/mcp.py#tool_response
- src/pmem/hooks/mcp.py#draft_key
revision: git:0c43c31
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 覆盖
- 记忆丢失
- draft_id
- 别名
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
结论：同一对话里对同一模块写第二条记忆时，前一条被覆盖（记忆丢失/被顶掉）的风险已修复。
现在只有议题（entity，不分大小写，按 modules.yaml 归一）也相同时，才自动注入 draft_id 覆盖本对话写过的草稿；
不同议题会各自新建。

原因回顾：闸门原先按模块记录本对话写过的记忆 id，record_memory 的 PreToolUse 只要没带 draft_id 就注入这个 id。
Claude Code 和 Codex 的文档明确支持 PreToolUse 返回 updatedInput（Codex 对 MCP 工具即“替换参数对象”），所以这个风险在多工具接入后必然触发。

同时修了写入、检索结果的解析。以前用正则在整个 payload 里找第一个 "module" 和 "id"，会先命中 tool_input 里 Agent 传的别名（如 Puzzle），导致：
- 草稿按别名记录，下次匹配不上；
- “改了模块却没写记忆”的提醒误报。
现在逐层解开 JSON（Cursor 的 result_json 是 content[].text 里再套一层 JSON 字符串；Claude/Codex 是 tool_response 内容块），找到带 ok 的 pmem 返回对象，跳过 tool_input，模块名再按注册表归一。
ok 不为 true 时不记。

验证：
- 20 份真实 Cursor afterMCPExecution 载荷，经生产解析器（含 GBK 乱码回转）全部解析成功；
- 单测覆盖同议题覆盖、异议题新建、嵌套返回、失败返回。
