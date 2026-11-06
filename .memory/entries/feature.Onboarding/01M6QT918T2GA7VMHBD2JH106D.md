---
id: 01M6QT918T2GA7VMHBD2JH106D
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_FULL
- src/pmem/generate/integrations.py#setup_cursor
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 默认 Hooks=full；Windows 与 Cursor 同开清空 Claude
verify: pmem doctor 显示 Hooks=full；.cursor/hooks.json 含 afterFileEdit；.claude/settings.json
  无 pmem Hook
applies: pmem init --hooks auto|full
---
需求：用户要求恢复之前最有效方案，并保证不乱弹黑框。
行为：pmem init --hooks auto|full 写入完整 CURSOR_HOOKS_FULL；Codex 同步完整；
Windows+Cursor 时 Claude Hooks 清空。
防弹窗：Hook=pmemw、MCP=pmem、无 .cmd/||、无双开 Claude、doctor 告警控制台 python。
入口：pmem init（默认 auto→full）；可选 --hooks quiet。
