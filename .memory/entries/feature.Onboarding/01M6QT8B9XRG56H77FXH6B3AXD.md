---
id: 01M6QT8B9XRG56H77FXH6B3AXD
module: feature.Onboarding
entity: Hooks
kind: correction
status: active
supersedes:
- 01M6QT17TPT3DEFJZT127PH91P
- 01M6JQ0XY5AHJYSWE6D0P3ZGKY
- 01M6JRCD0YDAN3TDZ3VCNKBPGC
anchors:
- src/pmem/generate/templates.py#cursor_hooks
- src/pmem/generate/templates.py#claude_hooks
- src/pmem/cli/doctor_cmd.py
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 默认恢复 full；禁再拆闸门，用 pmemw 防弹窗
verify: cursor_hooks('auto') 含 afterFileEdit 与 Read；claude_hooks(auto, paired_with_cursor=True)
  在 win32 为空；pytest tests/test_integrations.py::test_cursor_hooks_auto_is_full_everywhere
  -q
applies: 所有平台；pmem init --hooks auto|full
---
更正：Windows 上把 auto 默认成 quiet、再逐步拆成「只拦 MCP」是错的，记忆系统效果明显变差。
正确默认：auto = full（完整闸门 + 读码摘要 + session/prompt/stop + afterMCP + afterFileEdit + preCompact）。
Hook 命令用 pmemw，MCP 用 pmem。
Windows 与 Cursor 同开时清空 Claude Hooks（防双开翻倍弹窗），不是拆 Cursor 闸门。
quiet 仅作可选项：去掉读码摘要，闸门仍全留；禁止再拆 Write/Edit/Shell。
