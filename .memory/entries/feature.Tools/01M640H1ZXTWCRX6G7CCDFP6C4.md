---
id: 01M640H1ZXTWCRX6G7CCDFP6C4
module: feature.Tools
entity: SeenFill
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#search
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 排除：无 query 的模块速览不要按已见扩页
---
排除：无 query 的模块速览也按对话已见扩页。

扩到内部 limit>5 会跳过非防错条数上限；第二次检索还会把刚收紧的结论又填满名额。扩页只用于带 query 或 path、且本对话已给过全文的再查。
