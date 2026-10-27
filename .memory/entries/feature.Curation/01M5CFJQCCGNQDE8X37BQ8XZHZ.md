---
id: 01M5CFJQCCGNQDE8X37BQ8XZHZ
module: feature.Curation
entity: Merge
kind: decision
status: active
supersedes:
- 01M4Z58VYP1ZT8X81SW5TTQXCB
anchors:
- src/pmem/cli/compact_cmd.py#run_compact
- src/pmem/service/curation.py#compact_groups
- src/pmem/service/record.py#_record
- src/pmem/service/status.py#revert
- src/pmem/generate/templates.py#COMPACT_SKILL
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 零碎记忆由 Agent 按 pmem-compact 合并，pmem 不做自动摘要；可 compact --undo
aliases:
- 合并记忆
- compact
- 零碎记忆
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
决定：零碎记忆的合并由 Agent 按 pmem-compact 技能完成。
pmem 负责：找出可合并的议题（同模块、同实体不分大小写，有效记忆不少于 5 条）、按 (note_date, id) 输出全部正文、通过 supersedes 隐藏旧记忆，以及（更正：新增）pmem compact --undo 撤销合并。
不做自动摘要：哪些结论已被推翻只有读懂正文才能判断。
依据：TileMatch 853 条里 45 个议题各积累 5 条以上（共 303 条）；查询时前 3 条常是同一方案的三个演进阶段、互相矛盾。合并 13 条为 2 条后，相关查询第 1、2 条都是完整现状。
规则：替代旧记忆的写入，只有被替代的记忆里至少一条仍然现行、或带了 draft_id 时才不受每日上限约束（更正：旧记忆写的是无条件豁免）；
没填 anchors 时继承被替代记忆的关联代码，最多 10 个；
替代 2 条以上时只受 1200 字硬上限。
风险：合并后的记忆日期是合并当天，排序有时效加分；每日上限把已被替代的记忆也计入当天条数。
