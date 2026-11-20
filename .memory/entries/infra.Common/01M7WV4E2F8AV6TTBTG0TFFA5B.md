---
id: 01M7WV4E2F8AV6TTBTG0TFFA5B
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M7WJMFJ6CVTTTSNC11A8RDGM
anchors:
- README.md
- docs/pmem-guide.html
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-21'
summary: 效果栏与 Wiki 须同步当前版本 0.7.1
verify: README/手册含「当前版本 0.7.1」
applies: 改 README/手册效果表、Wiki 或发版同步效果数字时
---
需求来源：发 0.7.1 时同步效果栏与 Wiki 口径。

必须保持：
1) README「效果」与手册「收益与适用场景」开头有「当前版本 0.7.1」表：命中率、记忆被采用、改前真查、功能记录覆盖、结束提醒后真写、防错类占比、Claude/Codex 真实会话可用、v0.7 能力行（含 0.7.1 补丁说明）。
2) 「能省多少」表本仓库列与当前 report 对齐；注明 0.7.1 口径与报告日期。
3) GitHub Wiki（mry-ship/pmem.wiki）Home「当前版本」与更新记录须跟主仓版本；须另仓 push，只推主仓不更新 Wiki。
