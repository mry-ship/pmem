---
id: 01M5CAVVGXA51B2NVZEZ46K4YA
module: feature.Wiki
entity: Applies
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Wiki 条目显示适用条件
aliases:
- 适用条件
- applies
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
---
用户要求（2026-10-19）：记忆的适用条件要让人看得到，避免在前提不同的场景里照搬。
必须保持：Wiki 每条记忆在正文之后、“怎么验证”之前显示“适用条件：…”（有 applies 时）；功能记录和规划按类型中文名“功能”“规划”显示。
入口：generate/wiki.py 的条目渲染。
