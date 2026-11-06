---
id: 01M6QTAW8P5GQNRKDRDZN46MC8
module: feature.Onboarding
entity: McpEnable
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/mcp_enable.py#enable_project_mcp
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 不要写用户级 mcpServers 来启用 pmem，改走各家项目级信任存储
verify: 对比 doctor：有项目批准且用户级无 pmem
---
排除把 pmem 再写回用户级 ~/.cursor/mcp.json：多项目会串 root，且与既有 exclusion McpRoot 冲突。
改为：Cursor 用项目批准哈希、Claude 用项目 enabledMcpjsonServers、Codex 用项目 trust_level。
批准后当前 Cursor 窗口若仍 disconnected，需要 Reload Window 才能让内存中的 MCPService 重读批准名单。
