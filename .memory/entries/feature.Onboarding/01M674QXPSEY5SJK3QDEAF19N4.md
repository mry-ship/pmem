---
id: 01M674QXPSEY5SJK3QDEAF19N4
module: feature.Onboarding
entity: McpRoot
kind: exclusion
status: active
supersedes: []
anchors:
- .cursor/mcp.json
- src/pmem/generate/templates.py#MCP_SERVER
revision: git:a6de816
author: yanghu
note_date: '2026-10-31'
summary: 本仓mcp.json禁止提交本机绝对路径，跨项目粘错root应禁用用户级pmem
scope: project
verify: list_modules 返回 project_root=/Users/yanghu/Desktop/pmem；.cursor/mcp.json 仍为
  ${workspaceFolder}
applies: 本仓（mry-ship/pmem）与本机多项目并用 Cursor 用户级 pmem 时
aliases:
- MCP root
- workspaceFolder
- 用户级 mcp
source:
  conversation: 627a8ac5-6329-432f-8f96-52c21e1befc2
---
排除：把本机绝对路径（如 /Users/.../pmem）写进本仓 .cursor/mcp.json 并提交到 mry-ship/pmem。
原因：仓库是共享模板，init 与 MCP_SERVER 约定是 --root ${workspaceFolder}；绝对路径只对本机有效，会弄坏其他克隆与 CI。
现象：用户级 ~/.cursor/mcp.json 的 pmem-mcp-serve 常驻后可能粘在上一个项目（如 pmem-art），list_modules 的 project_root 指错仓。
正确修法：本仓保持 ${workspaceFolder}；本机禁用用户级全局 pmem（disabled），让各项目 .cursor/mcp.json 各自起服务；改完重载 MCP。
验证：list_modules 的 project_root 等于当前打开仓；git diff .cursor/mcp.json 无绝对路径。
