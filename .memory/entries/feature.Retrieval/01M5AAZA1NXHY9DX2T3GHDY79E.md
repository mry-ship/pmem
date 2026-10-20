---
id: 01M5AAZA1NXHY9DX2T3GHDY79E
module: feature.Retrieval
entity: Ranking
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#search
- src/pmem/index/anchors.py#anchor_affinity
- src/pmem/service/search.py#_search
revision: git:8e4415f
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 按路径检索
- 锚点加分
- 只查前五条
- 排序不准
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：按文件检索（search_memory 传 path）时，锚点就是这个文件的记忆加 0.3 分，锚点在同一目录的加 0.1 分（不区分大小写，去掉 #符号 后比较）。只加分不过滤，没有锚点的记忆排序不变。
原因：原先 path 只用来定位模块，不带 query 时相关度全为 0，排序只剩新旧和类型加分；一段时间集中改模块的某一方面后，改另一方面的文件时前 5 条全是不相干的近期记忆。写记忆时填的锚点在检索里完全没用上。
取值依据：BM25 按批内最大值归一化、相关度在 0～1 之间，0.3 在只传路径时足以压过时效差异（0.7～1.0 倍），带 query 时只起辅助作用。
本仓库 145 条现行记忆里只有 2 条没有锚点、119 条写到函数（未填时闸门会自动补本对话改过的文件），所以锚点缺失吃亏的风险很小。
风险：模块层面刚定的新方向若锚点不在当前文件，可能排到第 5 名以后，靠 memory_graph 和读代码摘要兜底。没有做“固定留名额”，避免规则变复杂。
