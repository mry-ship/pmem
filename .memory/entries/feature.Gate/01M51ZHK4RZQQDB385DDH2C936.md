---
id: 01M51ZHK4RZQQDB385DDH2C936
module: feature.Gate
entity: ForeignTool
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#_from_pmem
- src/pmem/hooks/mcp.py#on_after_mcp
- src/pmem/hooks/mcp.py#foreign_tool
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 同名工具
- 别家记忆服务
- TileMatch
- 误登记
- 来源标记
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
决定：别的记忆服务（如 TileMatch 的 dev-memory）也叫 search_memory / record_memory 时，闸门不能把它的结果当成“查过 pmem”。
Cursor 传给 Hook 的 MCP 工具名不带服务名（spike 抓包实测：tool_name 就是 search_memory，可见字段没有服务信息），所以由 pmem 自己在返回里加来源标记：

- pmem 的 MCP 返回统一带 "server": "pmem"。
  afterMCPExecution 只在以下任一成立时登记“已查过”：带该标记；
  工具名里有服务名 pmem（Claude Code、Codex 的 mcp__pmem__*）；
  返回的记忆 id 在本仓库 .memory/entries 里能找到（兼容升级后没重启的旧版服务）。
  否则记 foreign_search 事件，不登记。
  别家工具即使返回空结果也不算。
- 调用前（preToolUse）分不出来源，参数仍会注入给别家工具；实测 TileMatch 照常返回，无害。载荷带了非 pmem 的服务信息时不注入。

风险：升级 pmem 后没重启的旧版 MCP 服务返回空结果时不算查过，block 档会一直拦；
改用终端 pmem search 或重启 MCP 即可。
规则里也写明 pmem 的 MCP 不可用或只有同名工具时改用终端 pmem search。
