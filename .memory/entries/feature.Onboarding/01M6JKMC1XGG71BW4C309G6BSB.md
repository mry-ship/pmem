---
id: 01M6JKMC1XGG71BW4C309G6BSB
module: feature.Onboarding
entity: McpRoot
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#MCP_SERVER
- src/pmem/cli/doctor_cmd.py
- src/pmem/server/app.py#resolve_root
revision: git:e51a54a
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: init 生成 MCP 用 pmem；doctor 检出用户级冲突与 pmemw MCP
verify: uv run pytest tests/test_cli_flow.py tests/test_server.py -q；pmem doctor 对用户级
  pmem 告警
applies: Cursor 接入 pmem 的项目
verified: '2026-11-06'
verified_at: '2026-11-06T15:06:02.900+08:00'
---
需求：用户级与项目级同名 pmem、以及 MCP 误用 pmemw，导致 discovery 失败。
必须保持：项目 .cursor/mcp.json 为 pmem serve --root \（禁止提交本机绝对路径）；
Hooks 仍 pmemw；
doctor 警告用户级重复注册与 pmemw MCP；
resolve_root 回退 WORKSPACE_FOLDER_PATHS。
入口：pmem init / templates.MCP_SERVER / doctor_cmd。
