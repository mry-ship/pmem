---
id: 01M6JRCD0YDAN3TDZ3VCNKBPGC
module: feature.Onboarding
entity: WindowsConsole
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_QUIET
- src/pmem/generate/templates.py#claude_hooks
revision: git:87ba295
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: Cursor 经 PowerShell 起 Hook；quiet 只留闸门+MCP
verify: hooks 日志 Command 前有 PowerShell 转发；quiet 后 hooks.json 仅 preToolUse+afterMCP；与
  Cursor 同开时 Claude Hooks 为空
applies: Windows + Cursor；项目可有 .claude/settings.json
---
结论：Cursor 在 Windows 上经 PowerShell 转发 Hook stdin（见 hooks findings），每个 Hook 都可能弹一次控制台，与 pmemw 是否 GUI 无关。
Cursor 还会同时执行项目 .claude/settings.json（claude-project config），与 .cursor/hooks 叠加翻倍。
因此 Windows quiet 改为：Cursor 仅 preToolUse+afterMCPExecution；
与 Cursor 同开时清空 Claude 侧 pmem Hook。
读码摘要/stop/prompt/终端 search 登记需 --hooks full。
应急可用 --hooks off。
