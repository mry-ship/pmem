---
id: 01M52GTB9Y9ZEE2G2PBTDNV8XV
module: infra.Common
entity: Docs
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/brief.py#_search
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:fe52436
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 文档
- 使用手册
- README
- 简要输出
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：v0.2 的种子记忆、健康报告、模块迁移、归档上线后，用户文档三处同步更新：README（可选操作表与常用命令）、docs/pmem-guide.html（GitHub Pages 使用手册：接入步骤、后续维护、常用说法、核心概念里的状态、命令行表、整理与维护）、docs/architecture.md（各包职责与命令分发表）。search --brief 在种子记忆的类型后标“（种子，待确认）”，和闸门摘要一致。

原因：手册是队友接入的主要入口，新命令只写在 README 时队友看不到；状态变更只开放给命令行、MCP 不提供，也需要在手册里写明。

风险：三份文档和设计文档第 14 节各自维护同一份命令清单，以后加命令时容易漏改其中一份；手册不在 pmem 闸门守护范围内（docs/** 被忽略），改动不会触发记忆检查。
