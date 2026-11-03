---
id: 01M6GYR0H7GVJBCT87HYN9T30T
module: feature.Onboarding
entity: WindowsConsole
kind: feature
status: active
supersedes: []
anchors:
- pyproject.toml
- src/pmem/generate/templates.py#HOOK_BIN
- src/pmem/generate/integrations.py#_is_pmem
- src/pmem/cli/doctor_cmd.py
revision: git:a6de816
author: 1002378395@qq.com
note_date: '2026-11-03'
summary: Hook/MCP 改用无控制台入口 pmemw，避免 Windows 弹黑框
verify: pmemw.exe PE Subsystem=2；hooks.json 命令含 pmemw hook；打开 Cursor 新窗口不再弹黑框
applies: Windows 上 Cursor/Claude/Codex 的 Hook 与 MCP
---
需求：Windows 上接入 pmem 的项目打开新窗口、跑 Hook 时会反复弹出控制台黑框。
根因：Cursor 拉起的是控制台子系统 pmem.exe；
每次工具 Hook 都是新进程。
做法：pyproject 增加 gui-scripts 入口 pmemw（同 main）；
init 生成的 Cursor/Claude/Codex Hook 与 MCP 改为 pmemw；
包装脚本优先 pmemw 再回退 pmem；
doctor 在 Windows 上仍用 pmem 时告警。
人在终端里继续用 pmem。
适用：已升级并重跑 init 的项目。
入口：pmemw hook / pmemw serve；
模板 HOOK_BIN。
