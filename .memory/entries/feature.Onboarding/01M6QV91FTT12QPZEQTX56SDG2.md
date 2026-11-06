---
id: 01M6QV91FTT12QPZEQTX56SDG2
module: feature.Onboarding
entity: WindowsConsole
kind: conclusion
status: active
supersedes:
- 01M6QV2K7PW26NHN6747GP4AH8
anchors:
- src/pmem/generate/templates.py#cursor_hooks
- .cursor/hooks.json
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 黑框是 Cursor 拉起 Hook；Windows 默认 quiet 保闸门去读码摘要
verify: pmem doctor 显示 Hooks=quiet（闸门+提醒）；pytest tests/test_integrations.py::test_cursor_hooks_auto_quiet_on_windows_keeps_gate
  -q
applies: Windows + Cursor；pmem init --hooks auto|quiet
---
结论：现场黑框来自 Cursor 每次拉起 pmemw hook（日志 Command: pmemw hook pre-tool），不是 pmemw 自建控制台。full 的 Read/Grep/afterFileEdit 触发太勤会狂闪。
处理：Windows auto 回到 quiet=闸门+提醒+Shell post 全留，去掉读码摘要；禁止再拆成只拦 MCP。
验证：hooks.json pre 含 Write|Shell；post matcher=Shell；无 afterFileEdit；Cursor hooks 日志可对照。
