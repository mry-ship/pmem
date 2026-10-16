---
id: 01M4Z8DKS76NGDNNKWYDQX29SW
module: feature.Tools
entity: WriteHints
kind: decision
status: active
supersedes:
- 01M4XF761SDVRGGZTADM82RZ13
anchors:
- src/pmem/core/quality.py
revision: git:9b97360
author: 1002378395@qq.com
note_date: '2026-10-15'
---
决定：写入质量问题只提示、不拦截。record 返回 hints，照常写入，可带 draft_id（终端用 --draft-id）覆盖。硬拦截会让 Agent 反复重试甚至干脆不写。

内容提示：以“新增/修复/改为…”开头且无原因类词语，提示像变更记录；通篇无原因类词语，提示缺“为什么”；超过 write.recommend_max（默认 600 字）提示。

原因类词语含“回归”“已知”“避免/防止/以免”：TileMatch 习惯用“回归：”“已知：”标风险，不算时 1072 条真实记忆 31% 被判缺原因且有明显误报，加上后 21%，抽样剩下的基本是实现流水账。

实体：只在有相近已有名字时提示（规整大小写/复数/符号后相同，或互相包含且短名≥4 字符，或相似度≥0.8），回放提示率 6%–12%。
doctor 只报相似度≥0.85 或规整后相同的实体对，TileMatch 上 9 组。
坑：阈值 0.5 时报出 347 组，几乎全是无关名字；
UI 这类短名被包含多是巧合。
全局规范名不算新实体。

TileMatch dev-memory 服务有一份独立副本（tilematch_dev_memory/quality.py，阈值相同），改原因词时两边一起改。
