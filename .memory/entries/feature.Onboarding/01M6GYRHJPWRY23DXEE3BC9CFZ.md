---
id: 01M6GYRHJPWRY23DXEE3BC9CFZ
module: feature.Onboarding
entity: WindowsConsole
kind: decision
status: active
supersedes: []
anchors:
- pyproject.toml
- src/pmem/generate/templates.py#HOOK_BIN
revision: git:a6de816
author: 1002378395@qq.com
note_date: '2026-11-03'
summary: Hook/MCP 用 pmemw，终端交互仍用 pmem
verify: pyproject 同时有 scripts.pmem 与 gui-scripts.pmemw
applies: 生成接入配置时
---
取舍：不用把主入口 pmem 改成 GUI（终端 print 会丢）；
单独 gui-scripts 名 pmemw 专给 Agent 拉起。
sessionStart 仍走 .memory/bin/pmem-hook，未安装时能提醒；
包装内优先 call pmemw。
排除：不靠 PowerShell -WindowStyle Hidden（仍可能闪一下），也不改 Cursor 本身。
