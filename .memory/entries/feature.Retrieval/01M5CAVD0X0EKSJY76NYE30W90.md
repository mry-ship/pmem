---
id: 01M5CAVD0X0EKSJY76NYE30W90
module: feature.Retrieval
entity: Layered
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#search
- src/pmem/index/graph.py#digest
- src/pmem/index/graph.py#file_features
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 检索分层：教训给全文，功能记录另列标题，不互相挤占
verify: pytest tests/test_feature_records.py
aliases:
- 冷热分层
- 功能记录
- 分组
---
用户要求（2026-10-19）：检索时教训不能被每次都写的功能记录挤掉；功能记录要能看到但只占少量上下文。
必须保持：MemoryIndex.search 带 feature_limit 时分层，items 只放教训（limit 条、全文），功能记录和规划另排进 features（只有标题，title_row）；
不带 feature_limit 时（写入时找相近记忆等）照旧混排。
读代码摘要 digest 只从教训里挑，末尾附至多 2 条锚点就是当前文件的功能记录（file_features）。
检索文本含 applies。
没做：物理分目录存放教训和功能记录（要迁移、收益相同）；手工维护的单个汇总文件（多人追加冲突、丢锚点和替代关系）。
入口：index/store.py 的 search，index/graph.py 的 digest、file_features。
