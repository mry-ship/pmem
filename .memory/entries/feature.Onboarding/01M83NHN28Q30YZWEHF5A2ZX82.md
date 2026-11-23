---
id: 01M83NHN28Q30YZWEHF5A2ZX82
module: feature.Onboarding
entity: Hooks
kind: correction
status: active
supersedes:
- 01M6JQ01GC48X8B0ZDGCN9F06K
- 01M6QT09KEB2HA6YGC5W7DWABV
- 01M6QT8B9XRG56H77FXH6B3AXD
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_QUIET
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/doctor_cmd.py
- src/pmem/generate/templates.py#cursor_hooks
- src/pmem/generate/templates.py#claude_hooks
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 默认 Hooks=full；quiet 必须留 Shell 事后登记
source:
  kind: document
---
更正汇总（Windows Hooks 档位；曾把 auto 默认成 quiet、再拆成只拦 MCP，都已否定）：

正确默认：auto = full。
完整闸门 + 读码摘要 + session/prompt/stop + afterMCP + afterFileEdit + preCompact。
Hook 命令用 pmemw，MCP 用 pmem。
Windows 与 Cursor 同开时清空 Claude Hooks（防双开翻倍弹窗），不是拆 Cursor 闸门。

quiet 只是显式选项，不是「没有 postToolUse」，更不是「preToolUse 只匹配 MCP」（那样闸门失效）。
quiet 须保留：sessionStart、beforeSubmitPrompt、preToolUse（Write|Edit|Shell|MCP…）、afterMCPExecution、stop，以及 postToolUse 且 matcher 仅 Shell（否则终端 pmem search 无法登记已查过）。
去掉的只有 afterFileEdit、preCompact，以及 postToolUse 对 Read|Grep|Glob|语义搜索。
Codex quiet 同样保留 Bash|apply_patch|MCP 与 prompt/stop，只去掉 PreCompact。
禁止再以弹窗为由拆掉 Write/Edit/Shell 闸门。

合并自 3 条更正。
