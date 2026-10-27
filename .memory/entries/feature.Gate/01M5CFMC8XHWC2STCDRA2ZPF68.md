---
id: 01M5CFMC8XHWC2STCDRA2ZPF68
module: feature.Gate
entity: Agents
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/agents.py#normalize
- src/pmem/hooks/agents.py#render
- src/pmem/hooks/shell.py#_unwrap
- src/pmem/hooks/shell.py#_stages
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Claude/Codex 与 Cursor 同等受闸门守护：PowerShell、提问摘要、前缀命令都要认
verify: pytest tests/hooks/test_agents.py tests/hooks/test_gate.py
aliases:
- Claude 适配
- Codex 适配
- PowerShell 工具
- sudo 前缀
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
需求：用户要求“codex 和 claude 的适配都得做好”。必须保持的行为：
- Claude Code 的 PowerShell 工具和 Bash 一样按终端命令核对（事前解析写入目标、事后快照、终端 pmem search 算查过）。
- Codex 与 Claude 一样，UserPromptSubmit 附问题涉及模块的摘要，PostToolUse 附读码摘要和 Hook 出错提醒（hookSpecificOutput.additionalContext）。
- 终端命令前的 sudo/env A=1/command/nohup/exec/time/nice/stdbuf 前缀要去掉再识别，>| 要当重定向；单独的 env 和 command -v 仍是只读。
入口：hooks/agents.py 的 normalize/render，hooks/shell.py 的 _unwrap。
