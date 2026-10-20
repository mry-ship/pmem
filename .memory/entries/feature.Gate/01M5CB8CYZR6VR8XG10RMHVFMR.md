---
id: 01M5CB8CYZR6VR8XG10RMHVFMR
module: feature.Gate
entity: LayeredDigest
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#on_after_mcp
- src/pmem/hooks/review.py#_offer_digest
revision: git:7866189
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 检索返回的功能记录计入已看过；只有无关功能记录时摘要不说没有记忆
verified: '2026-10-20'
verified_at: '2026-10-20T19:41:04.401+08:00'
---
功能记录分层后闸门必须保持的两点行为（v0.3.1 复查时补上）：
1. MCP 检索返回后登记“看过的记忆”时，features 组（功能记录和规划标题）和 items、timeline 一样计入：返回的 id 记为已返回，不限模块检索时 features 里出现的模块也算看过。
   否则只命中功能记录的全局检索不算看过该模块，报告里的返回数也偏少。
2. 读代码摘要：模块有现行记忆但全是功能记录、且都不在当前文件上时，提示“该模块现有的记忆都是功能记录，和这个文件无关的这里不列”，并给出 search_memory(module=...) 的查法，不能说“该模块还没有研发记忆”（模块有记忆，改前检查照样会拦）。
验证：pytest tests/test_feature_records.py -k "only_unrelated or registers_feature"
