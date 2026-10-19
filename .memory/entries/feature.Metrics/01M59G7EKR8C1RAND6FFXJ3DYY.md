---
id: 01M59G7EKR8C1RAND6FFXJ3DYY
module: feature.Metrics
entity: Contradiction
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#_contradictions
revision: git:1e8fc87
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 矛盾
- 冲突
- 自相矛盾
- 前后矛盾
- contradiction
---
决定：pmem health 新增“疑似互相矛盾的记忆”一节。
判定条件：同模块同议题、都现行、一条是 conclusion/decision 而另一条是 exclusion/correction、互相没有 supersedes、正文词集合（tokenize 的中文二字词 + 英文词）Jaccard 相似度 ≥ 0.15。
risk 不参与比较。
最多列 10 对，按相似度排序。
较早那条有核对日期且不早于较晚那条的写入日期时视为负责人已看过，不再提示，所以“两条都成立”的处理办法就是 pmem confirm 较早那条。

阈值依据（实测）：本仓库 100 条现行记忆里，同议题无关的一正一反记忆相似度最高 0.11；
TileMatch 599 条里最高 0.18 的一对（infra.Decoration / SyncDataRelease）正是真矛盾：后一条更正撤回了前一条的 releaseVersion 方案却没写 supersedes。
长正文会拉低 Jaccard，所以起初定的 0.3 会漏掉它。
排除：没有用否定词（不、没、取消）判断正负，中文正文里这些词到处都有，误报太多；只看记忆类型。

风险：同议题下“选定方案 + 排除另一方向”的正常组合用词很像时会误报，处理一次（confirm）后不再出现。
