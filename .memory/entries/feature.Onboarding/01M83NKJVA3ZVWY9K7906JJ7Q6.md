---
id: 01M83NKJVA3ZVWY9K7906JJ7Q6
module: feature.Onboarding
entity: Doctor
kind: decision
status: active
supersedes:
- 01M5CFKAKGSMQ4AZZVE6R73CM6
- 01M6JWT8QPMYQ8FKZTQWDQDTGN
anchors:
- src/pmem/cli/doctor_cmd.py#run_doctor
- src/pmem/cli/doctor_cmd.py#_agent_handlers
- src/pmem/cli/doctor_cmd.py#_recent_errors
- src/pmem/generate/templates.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: doctor 是接入后的唯一自检入口
aliases:
- 自检
- doctor
source:
  kind: document
---
决定：pmem doctor 是接入后的唯一自检入口。

检查：配置可读、模块覆盖率（目标 95%，列出未覆盖）、路径重叠、空壳模块、PATH 里的 pmem、语义模型、各 Agent 接入。
有 .cursor/mcp.json 或 hooks.json、或三家都没接时才检查 Cursor；
接了 Claude/Codex 的分别检查 Hooks、MCP 和技能。
只接 Claude/Codex 时不因缺 .cursor/mcp.json 报错。
Claude Hook 缺 PowerShell matcher 或 onFailure 时提示旧版。
项目级 MCP 仍须用户在各工具里手动启用一次。

输出：Hook 错误只统计近 24 小时（更早的不提示）；记忆数写成「现行记忆 X 条（记忆文件共 Y 个，其余已被替代或停用）」。测试里调用 doctor 要把 embedding.backend 设为 none，否则会预热真实模型。

合并自 2 条决定。控制台 python、when/facets、防弹窗文案在同议题功能记录里。
