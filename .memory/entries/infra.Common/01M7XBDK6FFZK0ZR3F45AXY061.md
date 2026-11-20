---
id: 01M7XBDK6FFZK0ZR3F45AXY061
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M7WV4E2F8AV6TTBTG0TFFA5B
anchors:
- README.md
- docs/pmem-guide.html
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 首页、手册和 Wiki 已同步到 0.7.2
verify: README 与手册含「当前版本 0.7.2」
applies: 改 README/手册效果表、Wiki 或发版同步效果数字时
aliases:
- 使用手册
- 首页
source:
  kind: conversation
---
需求来源：发 0.7.2 时同步 GitHub 首页和手册。

必须保持：
1) README「效果」与手册「收益与适用场景」开头有「当前版本 0.7.2」表，并写明效果数字沿用 2026-11-21 报告（本版不改排序和采用判定）。
   表里含命中率、记忆被采用、改前真查、功能记录覆盖、结束提醒后真写、防错类占比、Claude/Codex 真实会话可用、v0.7 能力行和 v0.7.2 能力行。
2) 手册页眉页脚、README 版本徽章为 0.7.2。命令说明含 source.kind、valid_from 与 pmem spec closed。
3) 架构说明和设计文档第 11 节命令清单含 spec closed 与生效日。Wiki 另仓：Home 的当前版本和更新记录写到 0.7.2，须单独推 pmem.wiki。

入口：README.md；docs/pmem-guide.html。
