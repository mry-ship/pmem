---
id: 01M6GYRK76VFYC7ZW3F8Z72A1Z
module: feature.Onboarding
entity: WindowsConsole
kind: correction
status: active
supersedes:
- 01M5CFJ675VP99EGB614E98AGE
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS
revision: git:a6de816
author: 1002378395@qq.com
note_date: '2026-11-03'
summary: Cursor Hook 现直接调 pmemw，不再调控制台版 pmem
verify: CURSOR_HOOKS 命令前缀为 pmemw hook
---
更正：旧结论说除 sessionStart 外直接写 pmem hook。现改为 pmemw hook（及 MCP command=pmemw），避免 Windows 控制台黑框。sessionStart 仍经包装脚本。
