---
id: 01M4XF761SDVRGGZTADM82RZ13
module: feature.Tools
entity: WriteHints
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/quality.py
- src/pmem/service.py
- src/pmem/cli/doctor_cmd.py
revision: git:a0936e7
author: 1002378395@qq.com
note_date: '2026-10-14'
---
决定：写入质量问题只提示、不拦截。record 返回 hints，记录照常写入，可带 draft_id 改写覆盖（终端版用 --draft-id）。硬拦截会让 Agent 反复重试，甚至干脆不写。

内容提示：
- 以“新增/修复/改为…”开头且没有原因类词语，提示像变更记录；
- 通篇没有原因类词语，提示缺“为什么”；
- 超过 write.recommend_max（默认 600 字）时提示。

用 TileMatch 853 条真实记忆回放，约 29% 会收到缺“为什么”提示，抽样多数确实只写了改动。

实体：写入时只在有相近已有名字时提示，标准是规整大小写、复数、符号后相同，或互相包含且短名不少于 4 字符，或相似度不低于 0.8。
回放中新实体提示率 12%。
doctor 只报很可能重名的实体对（规整后相同，或相似度不低于 0.85），TileMatch 上报出 9 组，如 Booster/Boosters。

坑：相似度阈值 0.5 时，doctor 在 TileMatch 上报出 347 组，几乎全是无关名字（如 Analytics/Animation）；
UI 这类短名被包含也多是巧合。
按“只用过一次的实体占比”判断碎片化同样不可靠，项目早期必然偏高。
全局规范名（modules.yaml 顶层 entities）不算新实体。
