---
id: 01M6R7NC7CQRSAD8E6QJTWKEX6
module: infra.Common
entity: McpEnable
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/generate/mcp_enable.py#_claude_project_keys
- src/pmem/generate/mcp_enable.py#enable_claude_project_mcp
- src/pmem/generate/mcp_enable.py#enable_codex_project_mcp
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: Claude 按目录名启用会误信任同名其它项目；用户配置写入非原子
verify: 同名两项目时只改当前 resolve 路径那一项；用户配置写入用临时文件再 replace
---
enable_claude_project_mcp 用 Path.name==项目目录名匹配 ~/.claude.json 里所有 projects 键，同名不同路径会被一并写入 enabledMcpjsonServers 并 hasTrustDialogAccepted=True。
应优先精确路径，basename 只作候选且需再校验 resolve。
另：~/.claude.json 与 ~/.codex/config.toml 直接 write_text，中途崩溃会损坏用户配置；
应像 anchors/doctor 状态一样 tmp+os.replace。
