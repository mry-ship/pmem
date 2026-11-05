---
id: 01M6N9SV1DW3MHA86GK8F35BS4
module: feature.Onboarding
entity: WindowsConsole
kind: correction
status: active
supersedes:
- 01M6JQ0XY5AHJYSWE6D0P3ZGKY
anchors:
- src/pmem/generate/templates.py#cursor_hooks
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/doctor_cmd.py
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: quiet 闸门去掉 Shell：否则每条终端仍弹窗
verify: cursor_hooks('quiet')['preToolUse']['matcher'] 不含 Shell
applies: Windows + pmem init --hooks quiet；TileMatch_iLar
aliases:
- quiet去Shell
verified: '2026-11-05'
verified_at: '2026-11-05T16:00:41.825+08:00'
---
更正：Windows quiet 原先 preToolUse matcher 仍含 Shell，Agent 一跑 pmem search/record 或任意 Shell 就触发 pmemw hook，Cursor 经 PowerShell 转发照样弹黑框。
已改：CURSOR_HOOKS_QUIET 与 TileMatch_iLar/trial 现场 hooks 去掉 Shell；
CODEX quiet 去掉 Bash。
闸门仍拦 Write/Edit/MCP。
验证：hooks.json matcher 无 Shell；
重开项目窗后 Shell 工具不再触发 pre-tool。
