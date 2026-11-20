---
id: 01M7X8R3V9CGRTKAETD3FED1QN
module: feature.Metrics
entity: AsOf
kind: feature
status: active
supersedes: []
anchors: []
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 断链检测等替代生效再隐藏
---
需求来源：演化图自检里的断链检测要和检索用同一套替代生效口径。

必须保持：
- 未来 valid_from 的后继先不把目标算进已隐藏。
- 没写 valid_from 的替代仍然立即生效。
- 记忆图上节点谁是现行，同样等生效日；显式替代边仍画出来。

入口：src/pmem/metrics/memmap.py 的 _broken；src/pmem/index/memmap.py 的现行节点。
