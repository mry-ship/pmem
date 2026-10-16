---
id: 01M51QHMP55X8Z4JRXVM609WZZ
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/brief.py#render_brief
- src/pmem/cli/main.py
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 乱码
- 精简输出
- brief
---
决定：命令行 search、graph、record 增加 --brief，输出每条一行的中文摘要（类型｜议题｜日期｜id：正文前 120 字，过期的下一行标“⚠ 需核实：原因”，末尾附提示和相关模块），默认仍输出 JSON 供程序解析。record 的 --alias、--anchor、--supersedes 改为可跟多个值（--alias 闪退 崩溃），也可重复写。

背景：终端乱码的根因不是 pmem 输出（已统一 UTF-8），而是 Windows PowerShell 5 把输出接给 Select-String 等命令时按 GBK 解码。JSON 太长时 Agent 习惯接管道筛选，于是乱码；--brief 让直接看输出就够用。另外 --alias 带空格的值没加引号时，原先会把第二个词当成未知参数直接报错。

注意：search 返回的 related 是字符串列表，graph 返回的是字典列表（module、via、entities），渲染时两种都要兼容，曾因此在真实仓库上报 TypeError。
