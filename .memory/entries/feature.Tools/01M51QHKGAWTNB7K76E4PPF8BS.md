---
id: 01M51QHKGAWTNB7K76E4PPF8BS
module: feature.Tools
entity: Similar
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service.py#_similar_memories
- src/pmem/index/store.py#search
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 相近记忆
- 写入慢
- 提速
---
决定：写入时找“相近记忆”（similar）只用关键词（BM25）排序，不加载语义模型。

原因：命令行 pmem record 每次是新进程，实测总耗时约 3 秒，其中语义模型（ONNX）加载约 1 秒，全花在找相近记忆上；而这一步只在同模块、同议题里找，条数通常个位数，关键词足够区分。改后写入不再触发模型加载。检索（search_memory）不受影响，仍是语义 + 关键词混合排序。

同时：写入的 anchors 全部只写到文件（没有 #）时，返回的提示里加一句“anchors 尽量写到函数”，因为按函数判断过期能大幅减少“需核实”误报。
