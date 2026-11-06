---
id: 01M6JQ0XY5AHJYSWE6D0P3ZGKY
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#cursor_hooks
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/doctor_cmd.py
revision: git:f034aa1
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: Windows 默认 Hooks=quiet（postToolUse 仅 Shell）
verify: hooks.json 的 pmem postToolUse matcher=Shell；doctor 显示 Hooks=quiet；终端 search+post
  后 Write 放行
applies: Cursor + Windows；pmem init --hooks
aliases:
- quiet hooks
- 少弹 shell
- 疯狂弹窗
verified: '2026-11-06'
verified_at: '2026-11-06T14:52:03.318+08:00'
---
功能：Windows 上 pmem init 默认 Hooks=quiet。

quiet 保留：sessionStart / beforeSubmitPrompt / preToolUse（闸门）/ afterMCPExecution（MCP 检索登记）/ stop，以及 postToolUse 且 matcher 仅 Shell（终端 pmem search 登记与写文件事后核对）。
quiet 去掉：afterFileEdit、preCompact，以及 postToolUse 对 Read|Grep|Glob|语义搜索（避免每次读代码弹 shell）。
full：完整读码摘要等；--hooks auto|full|quiet。
适用：Cursor + Windows；入口 pmem init --hooks。
