---
id: 01M5Y5A76Q776PEY25MKK5CGQH
module: feature.Tools
entity: SeenDedupe
kind: feature
status: active
anchors:
- src/pmem/core/seen.py#claim_handoff
- src/pmem/hooks/mcp.py#_note_cli_calls
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: CLI 变量模块名用 * 交接，保证对话内折叠仍生效
verify: uv run pytest tests/test_quality_efficiency.py -k "handoff or shell_variable
  or collapsed"
applies: 改对话内去重或终端交接时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：对话内重复约 10%（目标曾 <5%），余量来自终端循环变量写模块名。
必须保持：Hook 对 search/graph 在解析不出 --module/--path 时 note_handoff([*])；
CLI claim 认领 * 或精确模块；
空 modules 仍只服务全局检索。
MCP 带 source_conversation 的去重、full=true 取全文、字段说明每对话一次等既有行为不变（本条不替代那些功能记录）。
入口：src/pmem/core/seen.py、src/pmem/hooks/mcp.py#_note_cli_calls。
