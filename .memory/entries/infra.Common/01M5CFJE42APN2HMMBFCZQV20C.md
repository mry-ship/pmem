---
id: 01M5CFJE42APN2HMMBFCZQV20C
module: infra.Common
entity: Docs
kind: decision
status: active
supersedes:
- 01M52GTB9Y9ZEE2G2PBTDNV8XV
anchors:
- src/pmem/cli/brief.py#_search
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 新命令要同步改 README、手册、architecture 和设计文档第 11 节
aliases:
- 文档
- 使用手册
- README
- 简要输出
verified: '2026-10-23'
verified_at: '2026-10-23T20:59:06.261+08:00'
---
决定：v0.2 的种子记忆、健康报告、模块迁移、归档上线后，用户文档三处同步更新：README（可选操作表与常用命令）、docs/pmem-guide.html（使用手册：接入步骤、后续维护、常用说法、状态、命令行表、整理与维护）、docs/architecture.md（各包职责与命令分发表）。
search --brief 在种子记忆的类型后标“（种子，待确认）”，和闸门摘要一致。
原因：手册是队友接入的主要入口，新命令只写在 README 时队友看不到；状态变更只开放给命令行，也要在手册写明。
风险：三份文档和设计文档 pmem-design.md 第 11 节“日常维护”的命令清单各自维护（更正：旧记忆误写为第 14 节，第 14 节是版本规划），加命令时容易漏改；docs/** 被闸门忽略，改文档不会触发记忆检查。
