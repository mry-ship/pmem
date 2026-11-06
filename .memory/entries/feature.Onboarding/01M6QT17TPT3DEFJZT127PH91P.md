---
id: 01M6QT17TPT3DEFJZT127PH91P
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes:
- 01M6ND2J4BPMFDR4HSRZ4ZSVFM
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_QUIET
- src/pmem/generate/templates.py#CODEX_HOOKS_QUIET
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: quiet 恢复闸门+提醒，postToolUse 仅 Shell
verify: pytest tests/test_integrations.py tests/test_cli_flow.py -q；pmem doctor 显示
  Hooks=quiet（闸门+提醒）
applies: Windows；pmem init --hooks quiet|auto
---
需求：用户明确「以前也没弹黑框，别乱拆，得保证闸门都在」。
行为：CURSOR_HOOKS_QUIET = 闸门全集 + 提醒 + postToolUse(Shell)；不再 MCP-only。
CODEX_HOOKS_QUIET 保留 Pre/Post/prompt/stop（含 Bash），无 PreCompact。
Windows 与 Cursor 同开时仍清空 Claude Hooks 防双开。
入口：pmem init --hooks quiet|auto；doctor 识别「闸门+提醒；postToolUse 仅 Shell」。
