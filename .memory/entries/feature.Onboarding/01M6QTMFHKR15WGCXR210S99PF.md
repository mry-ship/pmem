---
id: 01M6QTMFHKR15WGCXR210S99PF
module: feature.Onboarding
entity: McpEnable
kind: feature
status: active
supersedes:
- 01M6QTACYXP344F5M4T4390K87
anchors:
- src/pmem/generate/mcp_enable.py#enable_project_mcp
- src/pmem/generate/integrations.py#setup_cursor
- tests/test_mcp_enable.py
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: init 自动项目级启用三家 Agent 的 pmem MCP，测试环境不写本机状态
verify: uv run pytest tests/test_mcp_enable.py tests/test_cli_flow.py -q；pmem doctor
  显示已项目级批准
applies: pmem init 接入的项目；含 setup_* 的测试默认跳过本机写入
aliases:
- MCP自动启用
- 项目级MCP
---
需求：用户要求 pmem init 自动启用项目级 MCP（非用户级），覆盖 Cursor / Claude Code / Codex。
必须保持：项目 MCP 仍落在各项目配置文件；
Cursor 写入本机 approvedProjectMcpServers（哈希对齐 Cursor，含未解析 ${workspaceFolder}）；
Claude 项目 enabledMcpjsonServers 含 pmem；
Codex 项目 trust_level=trusted；
pytest 下默认不写本机状态（PMEM_SKIP_MCP_ENABLE=0 才测写入）；
禁止写用户级 ~/.cursor/mcp.json。
入口：src/pmem/generate/mcp_enable.py（setup_* 调用）；doctor 检查批准；路径归 feature.Onboarding。
