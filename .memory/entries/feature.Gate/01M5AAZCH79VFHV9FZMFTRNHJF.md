---
id: 01M5AAZCH79VFHV9FZMFTRNHJF
module: feature.Gate
entity: PromptReview
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/graph.py#digest
- src/pmem/hooks/gate.py#_offer_digest
revision: git:8e4415f
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 读代码摘要
- digest
- 摘要不准
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：读代码、限定模块搜索时附的模块摘要（6 条，每议题最多 2 条，按排除项、风险、更正、决定、结论排序）改为：锚点就是正在看的文件的记忆先占至多 3 个名额，其余名额照旧。
原因：原先摘要只看类型和新旧，模块里排除项多或最近集中写了另一方面时，和正在看的文件相关的结论进不了摘要。
只给一半名额是为了保住模块层面的排除项和风险（改之前最该知道的两类）。问题里提到模块时没有具体文件，摘要不变。
与检索的锚点加分（feature.Retrieval / Ranking）用同一个判断函数 anchor_affinity。
