---
id: 01M5EJPXD79NNCNJ16G5CRA705
module: feature.Retrieval
entity: Ranking
kind: decision
status: active
supersedes:
- 01M5AAZA1NXHY9DX2T3GHDY79E
- 01M5CFJ9F6S0600RH2HKGHR320
anchors:
- src/pmem/index/store.py#search
- src/pmem/index/anchors.py#anchor_affinity
- src/pmem/service/search.py#_search
- src/pmem/index/store.py#_score
- docs/pmem-guide.html
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 排序以相关度为主、时效占 30%，不按时间排；按文件检索时锚点加 0.3/0.1 分
aliases:
- 检索排序
- 锚点加分
---
决定：检索排序以相关度为主、时效只占 30% 权重（90 天半衰期，系数 0.7～1.0，按核对日期算），不要改成按时间排；按文件检索时给锚点加分。
锚点加分：search_memory 传 path 时，锚点就是这个文件的记忆加 0.3 分，锚点在同一目录的加 0.1 分（不区分大小写，去掉 #符号 后比较）。只加分不过滤，没有锚点的记忆排序不变。
原因：原先 path 只用来定位模块，不带 query 时相关度全为 0，集中改模块某一方面后，改另一方面的文件时前 5 条全是不相干的近期记忆。
BM25 按批内最大值归一化在 0～1 之间，0.3 在只传路径时足以压过时效差异，带 query 时只起辅助作用。
当时 145 条现行记忆只有 2 条没锚点。
旁证：与参考实现（tilematch-dev-memory，LanceDB + nomic-embed-text）在 TileMatch 853 条真实记忆上对比，13 个限定模块查询前三命中 pmem 9/13、参考实现 4/13，较早记忆 4/6 对 0/6。
差距来自排序：参考实现先取 max(limit×5,20) 条候选再按日期截取，≤20 条的模块（53 个中 42 个）查询词完全不影响结果，老结论被新记忆挤掉。
对比现在在 docs/pmem-guide.html，不在 README。
风险：模块层面刚定的新方向若锚点不在当前文件，可能排到第 5 名以后，靠 memory_graph 和读代码摘要兜底；没做“固定留名额”，避免规则变复杂。合并自 2 条记忆。
