---
id: 01M5CFK93YEEHZXDZH8M6H1K06
module: feature.Retrieval
entity: EntryText
kind: decision
status: active
supersedes:
- 01M5ACNRG3ZBTCTPSW6PYR5EKA
anchors:
- src/pmem/index/store.py#entry_text
- src/pmem/index/store.py#entry_row
- src/pmem/index/store.py#title_row
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 检索文本含 summary、verify、applies；全文条目只返回显式写的 summary
aliases:
- 标题检索
- summary
---
决定（v0.3）：检索文本加入 summary、verify 和 applies，用标题、验证方法或适用条件里的说法也能搜到。
items 里的全文条目只在显式写了 summary 时返回该字段（自动标题和正文重复，不返回），verify、全项目级 scope 照常返回。
更正：“自动标题不返回”只对全文条目成立；features 分组和对话内已给过全文、被折叠成标题的条目，返回的 summary 是 entry.title，包括自动生成的标题。
