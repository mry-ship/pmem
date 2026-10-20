---
id: 01M5CSD7D15G1NFSH0CZ1S4DW4
module: feature.Retrieval
entity: SpreadBatches
kind: correction
status: active
supersedes:
- 01M5CQTZBK0BNWCS4CJG94VDXT
- 01M5CAVE8WNP4ESCMD549MGZXS
anchors:
- src/pmem/index/store.py#_spread_batches
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 同批超额已改为降权；名额内须保持原排序，否则语义命中被挪后
verify: uv run pytest tests/index -k batch；uv run python scripts/eval_real_queries.py
  run --set real --ranks，看「stale 关联代码 同义」是否在前 3 返回 01M4X40BBTRXTJT8KJS5DJ3AB0
aliases:
- 硬剔除
- 批次名额
- 降权
---
更正 SpreadBatches 风险“同一批最多 2 条是硬剔除”：已改成降权，超额的相关记忆排在其他相关结果之后、不相关的之前，不再整条丢失；limit 为 0 时也不再返回 1 条（同时替代“名额为 0 时仍返回 1 条”的风险）。
踩过的坑：第一版把结果分成“名额内相关 / 超额相关 / 名额内不相关 / 超额不相关”四档，名额内只靠语义命中（关键词为 0）的正确答案被挪到弱关键词命中之后，真实题 top3 比硬剔除还低。名额内必须保持原排序，只移动超额的。
证据（2026-10-20 同一份记忆库，eval_real_queries.py）：真实题集 top3 语义+关键词 79→82/91、MRR 0.645→0.656；
仅关键词 71→74/91、MRR 0.595→0.611；
路径题集、别名题集不变。
「stale 关联代码 同义」等 3 题的答案 01M4X40BBTRXTJT8KJS5DJ3AB0 回到第 3。
