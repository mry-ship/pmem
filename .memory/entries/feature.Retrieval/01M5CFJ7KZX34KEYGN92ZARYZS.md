---
id: 01M5CFJ7KZX34KEYGN92ZARYZS
module: feature.Retrieval
entity: Ranking
kind: exclusion
status: active
supersedes:
- 01M4X7E1GSMHD1FQCKPT7X562W
anchors:
- src/pmem/index/store.py#search
- src/pmem/index/store.py#_bm25
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 不给检索加相关度阈值：真实数据上相关与无关分数重叠，任何阈值都误杀
aliases:
- 相关度阈值
- 无关结果
- 过滤
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
排除：不给检索结果加“相关度阈值”过滤无关条目——真实数据上分不开，任何阈值都会误杀真命中。
背景：模块里没有相关记忆时 search 仍返回 top-k 条无关记忆（system.AdChase 查“价格排序”等，grep 确认库里没有这类内容）。
证据（TileMatch 853 条真实记忆、21 个人工核对的查询，bge-small-zh-v1.5）：语义余弦无关查询最高 0.583，真命中最低 0.500，区间重叠；
BM25 按批内最大值归一化，首条永远是 1，不能当绝对相关度；
查询词覆盖率也不行（“计分规则”真命中覆盖率仅 0.33）。
同义改写基本找不回（闪退/崩溃、小圆点/红点），召回主要靠字面。
结论：维持返回 top-k，由 Agent 读正文判断。
更正旧记忆：教训默认返回 5 条全文（search.limit），另附最多 3 条功能记录标题（feature_limit），不是“每次仅 3 条”。
提升召回靠模块/实体归类和正文写全常用叫法（aliases），不是调阈值。
