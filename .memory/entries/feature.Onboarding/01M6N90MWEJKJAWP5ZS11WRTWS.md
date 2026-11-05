---
id: 01M6N90MWEJKJAWP5ZS11WRTWS
module: feature.Onboarding
entity: WindowsConsole
kind: decision
status: active
supersedes: []
anchors: []
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Art CLI 包装：Windows=pyw，Mac=python3，安装时整包改写
applies: Cursor-Pmem-Art 全仓 CLI 启动器
aliases:
- pyw包装
- 平台分流启动器
---
为什么：Agent 照抄技能/followup 里的命令；
Windows 写死 python3 必弹控制台。
做法：源码 skill_specs 保留 python3（Mac 可读）；
art_cli 统一入口，install/ensure_cursor_stubs 安装时整包改写技能、commands、规则、AGENTS/CLAUDE/手册；
运行时 converge followup/agentMessage 再改写一遍。
排除：只改 hooks、或只在规则里口头禁止 python3。
代价：同一仓在 Mac/Win 检出后生成物不同，换机需重跑 stubs/install。
