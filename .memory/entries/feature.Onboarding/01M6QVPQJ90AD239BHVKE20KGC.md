---
id: 01M6QVPQJ90AD239BHVKE20KGC
module: feature.Onboarding
entity: WindowsConsole
kind: correction
status: active
supersedes:
- 01M6QV91FTT12QPZEQTX56SDG2
anchors:
- src/pmem/vcs/base.py#run_tool
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 闪框不靠 quiet 削功能；run_tool 藏窗后保持 Hooks=full
verify: hooks.json 仍为 full；pytest tests/vcs/test_run_tool_no_window.py
applies: Windows + Cursor；pmem init --hooks auto|full
aliases:
- 黑框
- quiet
---
更正：先前结论“Windows 默认 quiet、去掉读码摘要以防黑框”已过时。
用户要求恢复 Hooks=full（含读码摘要/afterFileEdit），并单独修闪框。
真正可在不改闸门功能下消掉的那部分黑框，来自 Hook 内 git/svn 子进程缺少 CREATE_NO_WINDOW（见 feature.Storage RunToolNoWindow）。
仍成立：外层若 Cursor 用未藏窗的 pwsh/cmd 拉起 Hook，仍可能弹与 Hook 次数相当的控制台；那与 git 子进程闪框不是同一层。
auto/full 保持完整 CURSOR_HOOKS_FULL；quiet 仅作显式选项，不再当作 Windows 默认治闪方案。
