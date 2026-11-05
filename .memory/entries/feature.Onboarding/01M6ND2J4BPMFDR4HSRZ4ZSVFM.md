---
id: 01M6ND2J4BPMFDR4HSRZ4ZSVFM
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes:
- 01M6N9TZJ6KFD7YV473C3S7BRF
anchors:
- src/pmem/generate/templates.py#_CURSOR_QUIET_PRE_MATCHER
revision: git:6570dd2
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Windows quiet 闸门 matcher 只留 MCP
verify: pytest tests/test_integrations.py::test_cursor_hooks_auto_quiet_on_windows
  -q
applies: Windows；pmem init --hooks quiet|auto
---
需求：Windows quiet 不再因 Write 写 md 或 Shell 弹控制台。
行为：CURSOR_HOOKS_QUIET preToolUse matcher 为 MCP|record_memory|search_memory（无 Write/Edit/Shell）；
仍保留 afterMCPExecution；
CODEX_HOOKS_QUIET matcher 仍为 apply_patch|mcp。
入口：pmem init --hooks quiet|auto（Windows）。
代价：改代码 Write 不过 pre-tool，靠规则+afterMCP；
要硬闸门用 --hooks full。
适用：Cursor/Codex Windows。
