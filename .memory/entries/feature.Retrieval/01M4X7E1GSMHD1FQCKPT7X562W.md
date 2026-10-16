---
id: 01M4X7E1GSMHD1FQCKPT7X562W
module: feature.Retrieval
entity: Ranking
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py
revision: git:f131206
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
排除：不给检索结果加“相关度阈值”过滤无关条目——真实数据上分不开，任何阈值都会误杀真命中。

背景：查询在模块里没有相关记忆时，search 仍返回 top-k 条无关记忆（例：system.AdChase 查“价格排序”、activity.Jigsaw 查“奖励 重复”，经 grep 确认库里根本没有这类内容）。

证据（TileMatch 853 条真实记忆、21 个人工核对过的查询，bge-small-zh-v1.5）：
- 语义余弦：无关查询最高到 0.583（“苹果审核被拒”），真命中最低 0.500（level.DDA“连胜”）、0.535（“计分规则”），区间重叠。
- BM25 按批内最大值归一化，首条永远是 1，不能当绝对相关度；改用“查询词覆盖率”也不行：“计分规则”真命中覆盖率仅 0.33（只命中“计分”）。
- 同义改写基本找不回：“闪退”找不到 28 条写“崩溃”的记忆、“提示小圆点”找不到“红点”、“首充”找不到“破冰”。小模型对项目术语的语义泛化很弱，实际召回主要靠字面。

结论：维持返回 top-k（每次仅 3 条短正文），由 Agent 读正文自行判断是否相关。提升召回更有效的方向是模块/实体归类与记忆正文里写全常用叫法，而不是调阈值。检索延迟 1–14 ms/次（853 条）。
