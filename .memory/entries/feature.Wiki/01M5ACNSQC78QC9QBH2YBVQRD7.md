---
id: 01M5ACNSQC78QC9QBH2YBVQRD7
module: feature.Wiki
entity: Heading
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: Wiki 小标题用一句话标题，索引新增全项目通用一节
aliases:
- 小标题
- 全项目通用
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
---
决定（v0.3）：Wiki 每条记忆的小标题改为“类型 · 全项目（如有）· 日期 · 作者：标题”，有 verify 时单列“怎么验证”；历史和最近列表也用标题。索引页新增“全项目通用”一节，列出 scope: project 的记忆。
原因：原来小标题截正文前 80 字，常带“决定：”重复前缀，看不出结论。
