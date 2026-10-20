---
id: 01M5CAVE8WNP4ESCMD549MGZXS
module: feature.Retrieval
entity: SpreadBatches
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_spread_batches
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: _spread_batches 名额为 0 时仍返回 1 条，调用前要判断
aliases:
- 名额
- limit为0
---
风险：_spread_batches 是“先放进去再判断是否够数”，limit 传 0 时仍会返回 1 条。
现象：search.feature_limit 设为 0 时 features 里还是出现一条功能记录（单测 test_feature_limit_zero_hides_group 发现）。
处理：调用处 feature_limit 大于 0 才调用 _spread_batches。以后新增按名额截取的地方，名额可能为 0 时同样要在外面判断，或改造 _spread_batches 先判断再放。
