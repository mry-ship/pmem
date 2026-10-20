---
id: 01M5CQTZBK0BNWCS4CJG94VDXT
module: feature.Retrieval
entity: SpreadBatches
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_spread_batches
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 同一批最多 2 条是硬剔除：43% 教训所在批次超限，第 3 条起再相关也不返回
verify: uv run python scripts/eval_real_queries.py run --set real --ranks，看「stale
  关联代码 同义」是否返回 01M4X40BBTRXTJT8KJS5DJ3AB0
aliases:
- 分批
- max_per_batch
- 同一批
- 召回丢失
- 搜不到
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
风险：_spread_batches 对超过 max_per_batch（默认 2）的记忆直接跳过，不是降到后面；
结果列表又包含零相关度的记忆，所以同一批里第 3 条相关记忆会输给别的批次里完全不相干的记忆，limit 设到 30 也不会出现。
改成连续时间窗口分批后更明显：2026-10-20 本仓库 172 条现行教训分成 96 批，17 批超过 2 条、共 74 条（43%），最大一批 7 条（feature.Retrieval 早期记忆）。
证据：真实检索评测里「stale 关联代码 同义」等 3 题，答案 01M4X40BBTRXTJT8KJS5DJ3AB0 在 627b54f（固定时间桶）排第 3，当前因与前两条同批而完全不返回；真实题前三命中由 90% 降到 87%。
可选修法（未定）：超限的只降到其他相关结果之后、仍排在零相关的前面；或把 max_per_batch 提到 3。
