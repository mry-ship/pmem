---
id: 01M6QT09KEB2HA6YGC5W7DWABV
module: feature.Onboarding
entity: Hooks
kind: correction
status: active
supersedes:
- 01M6ND2J4BPMFDR4HSRZ4ZSVFM
- 01M6ND1V88R7NR8B0Z1H4935A8
- 01M6N83TNKSKKP14JFGFDTME01
- 01M6N9TZJ6KFD7YV473C3S7BRF
- 01M6N9SV1DW3MHA86GK8F35BS4
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_QUIET
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/doctor_cmd.py
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: quiet 禁止拆成只拦 MCP，闸门必须保留
verify: cursor_hooks('quiet') pre 含 Write|Shell；post matcher=Shell；pytest tests/test_integrations.py::test_cursor_hooks_auto_quiet_on_windows
  -q
applies: Windows；pmem init --hooks quiet|auto
---
更正：为消 Windows 弹窗把 quiet 收成「preToolUse 只匹配 MCP」是错的，闸门等于失效。
正确 quiet（与 01M6JQ0XY5AHJYSWE6D0P3ZGKY 一致）：保留 sessionStart / beforeSubmitPrompt / preToolUse（Write|Edit|Shell|MCP…）/ afterMCPExecution / stop，以及 postToolUse 且 matcher 仅 Shell。
去掉的只有 afterFileEdit、preCompact、以及 postToolUse 对 Read|Grep|Glob|语义搜索。
Codex quiet 同样保留 Bash|apply_patch|MCP 与 prompt/stop，只去掉 PreCompact。
禁止再以弹窗为由拆掉 Write/Edit 闸门；要硬摘要用 --hooks full。
