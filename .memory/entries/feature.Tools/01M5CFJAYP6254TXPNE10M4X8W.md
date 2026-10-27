---
id: 01M5CFJAYP6254TXPNE10M4X8W
module: feature.Tools
entity: Similar
kind: decision
status: active
supersedes:
- 01M51QHKGAWTNB7K76E4PPF8BS
anchors:
- src/pmem/service/record.py#_similar_memories
- src/pmem/service/record.py#_record
- src/pmem/index/store.py#_relevance
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 写入时找相近记忆只用关键词，不加载语义模型；锚点只到文件时给提示
aliases:
- 相近记忆
- 写入慢
- 提速
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
决定：写入时找“相近记忆”（similar）只用关键词（BM25）排序，不加载语义模型。
原因：命令行 pmem record 每次是新进程，实测约 3 秒，其中语义模型加载约 1 秒，全花在找相近记忆上；
而这一步只在同模块、同议题里找，条数通常个位数，关键词足够。
检索（search_memory）不受影响，仍是 0.6 语义 + 0.4 关键词混合。
同时：写入的 anchors 全部只写到文件时，返回提示说明后果并建议写到函数。
更正旧记忆的引文：实际提示是“anchors 只写了文件：该文件以后任何改动都会让这条记忆标为‘需核实’。
能定位到函数时写成 路径#函数名…”，不是“anchors 尽量写到函数”。
