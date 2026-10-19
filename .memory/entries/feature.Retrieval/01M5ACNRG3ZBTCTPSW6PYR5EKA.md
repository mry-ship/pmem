---
id: 01M5ACNRG3ZBTCTPSW6PYR5EKA
module: feature.Retrieval
entity: EntryText
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#entry_text
- src/pmem/index/store.py#_row
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 检索文本含 summary 和 verify；结果只返回显式写的 summary
aliases:
- 标题检索
- summary
---
决定（v0.3）：检索文本加入 summary 和 verify，用标题或验证方法里的说法也能搜到；检索结果只在显式写了 summary 时返回该字段（自动标题不返回，避免和正文重复），verify、全项目级 scope 照常返回。
