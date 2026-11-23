---
id: 01M83NKGQPY226YBZ8P7XHZYCP
module: feature.Tools
entity: SeenDedupe
kind: feature
status: active
supersedes:
- 01M5CVMP8TZEP8K6GMFAK15G8X
- 01M5Y5A76Q776PEY25MKK5CGQH
- 01M640J45KSQM1ARZRN4YMQGYF
anchors:
- src/pmem/service/search.py#SearchOps._hints_once
- src/pmem/server/app.py#build_server
- src/pmem/core/seen.py#claim_handoff
- src/pmem/hooks/mcp.py#_note_cli_calls
- src/pmem/service/search.py#_collapse_seen
- src/pmem/service/search.py#search
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 已见全文只回标题并扩页；提示同一对话只给一次
aliases:
- 去重
- seen
- 已见
source:
  kind: document
---
需求来源：对话内去重，避免已见标题占满名额、终端循环变量写模块名导致重复偏高。

必须保持：
1) 同一对话已返回全文的记忆再出现时只给标题（seen: true）并附 seen_hint；
   seen_hint 每次折叠都给。
   全文用 full=true 或命令行 --full。
   读代码摘要只给标题，不算给过全文。
   压缩后清空去重记录。
   没有对话 id 时不去重。
2) 同一对话、非 full、带 query、且已给过全文时，内部多取一页（不超过上限），折叠时先排未见全文再补已见标题，再截回原 limit。
   无 query 的模块速览（含只带 path、没有锚点命中）不扩页，以免冲掉「防错优先、结论最多 2 条」。
3) features_hint、applies_hint、verify_hint 同一对话只给一次（hint:<字段名>），压缩后可再给；没有对话 id 时每次都给。
4) Hook 对 search/graph 在解析不出 --module/--path 时 note_handoff([*])；
   CLI claim 认领 * 或精确模块；
   空 modules 仍只服务全局检索。
   MCP 带 source_conversation 的去重不变。

入口：service/search.py 的 search、_collapse_seen、_hints_once；core/seen.py claim_handoff；hooks/mcp.py _note_cli_calls。

合并自 3 条功能记录。排除项与交接锁、summary/verify/scope 规则仍是同议题的教训，未并入本条。
