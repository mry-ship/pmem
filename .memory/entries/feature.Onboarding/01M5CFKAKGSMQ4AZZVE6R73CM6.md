---
id: 01M5CFKAKGSMQ4AZZVE6R73CM6
module: feature.Onboarding
entity: Doctor
kind: decision
status: active
supersedes:
- 01M4X3ZRBXFCR3NE89YMGKNY3S
anchors:
- src/pmem/cli/doctor_cmd.py#run_doctor
- src/pmem/cli/doctor_cmd.py#_agent_handlers
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem doctor 是唯一自检入口；按实际接入的 Agent 分别检查
aliases:
- 自检
- doctor
- 接入检查
---
决定：pmem doctor 是接入后的唯一自检入口：配置可读、模块覆盖率（目标 95%，列出未覆盖目录）、路径重叠、空壳模块、各 Agent 的接入、PATH 中的 pmem、语义模型预热与近 24 小时 Hook 错误。
更正：接入检查不再只看 Cursor。
项目有 .cursor/mcp.json 或 hooks.json、或三家都没接时才检查 Cursor（mcp.json、hooks.json、规则、包装脚本）；
接了 Claude Code / Codex 的分别检查 Hooks、MCP 和技能（.claude/skills、.agents/skills），Claude 的 Hook 缺 PowerShell matcher 或 onFailure 时提示旧版。
只接 Claude/Codex 的项目不再因缺 .cursor/mcp.json 报错。
实测价值：新增 scripts/smoke_mcp.py 后 doctor 立即报出覆盖率 98.4% 并点名该文件。
注意：测试中调用 doctor 要把 embedding.backend 设为 none，否则会预热真实模型（4 秒变 14 秒）。项目级 MCP 要用户在各工具里手动启用或批准一次。
