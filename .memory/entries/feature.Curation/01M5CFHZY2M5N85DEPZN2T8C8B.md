---
id: 01M5CFHZY2M5N85DEPZN2T8C8B
module: feature.Curation
entity: WriteHints
kind: decision
status: active
supersedes:
- 01M4Z8DKS76NGDNNKWYDQX29SW
anchors:
- src/pmem/core/quality.py#content_hints
- src/pmem/core/quality.py#similar_entity_pairs
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 写入质量问题只提示不拦截；变更记录与缺原因提示只对教训生效
aliases:
- 写作提示
- hints
- 缺原因
- 变更记录
---
决定：写入质量问题只提示、不拦截。record 返回 hints，照常写入，可带 draft_id 覆盖。硬拦截会让 Agent 反复重试甚至干脆不写。
内容提示：以“新增/修复/改为…”开头且无原因类词语，提示像变更记录；通篇无原因类词语，提示缺“为什么”；超过 write.recommend_max（默认 600 字）提示。
更正：这两条“变更记录 / 缺原因”提示现在只对教训类（exclusion/risk/correction/decision/conclusion）生效；
功能记录和规划改为检查是否写了需求来源。
判断前先去掉开头的“决定：/结论：”等类型前缀，否则“决定”本身会被当成原因词。
原因类词语含“回归”“已知”“避免/防止/以免”：TileMatch 习惯用“回归：”“已知：”标风险，不算时 1072 条真实记忆 31% 被判缺原因且误报明显，加上后 21%。
实体：只在有相近已有名字时提示（规整后相同，或互相包含且短名≥4 字符，或相似度≥0.8），回放提示率 6%–12%。
doctor 只报相似度≥0.85 或规整后相同的实体对；
阈值 0.5 时报出 347 组几乎全是无关名字。
全局规范名不算新实体。
TileMatch dev-memory 服务有一份独立副本（quality.py，阈值相同），改原因词时两边一起改。
