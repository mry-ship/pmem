---
id: 01M4Z58VYP1ZT8X81SW5TTQXCB
module: feature.Curation
entity: Merge
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/compact_cmd.py
- src/pmem/service.py
- src/pmem/generate/templates.py
revision: git:f3e8e07
author: 1002378395@qq.com
note_date: '2026-10-15'
verified: '2026-10-16'
---
决定：零碎记忆的合并由 Agent 按 pmem-compact 技能完成。pmem 只负责三件事：找出可合并的议题（同模块、同实体且不分大小写，有效记忆不少于 5 条）、按时间输出全部正文、通过 supersedes 隐藏旧记忆。不做自动摘要：哪些结论已被推翻，只有读懂正文才能判断。

依据：TileMatch 853 条记忆里有 45 个议题各积累了 5 条以上，合计 303 条，占 36%。导入的记忆每条自成一批，“同批最多 2 条”的限制管不到它们，于是查“紧急盘 兜底 多解”时，前 3 条全是同一方案的三个演进阶段，结论互相矛盾。把 FarmSudoku/LevelFactory 的 13 条（2500 字）合并成 2 条（约 1150 字）后，5 个相关查询的第 1 或第 2 条都是合并后的完整现状，空出的名额让给了其他议题。

规则：
- 替代旧记忆的写入不受每日条数上限约束；
- 没填 anchors 时继承被替代记忆的关联代码，最多 10 个；
- 替代 2 条以上时，不再提示“超过 600 字”，只受 1200 字的硬上限约束。

风险：
- 合并后的记忆日期是合并当天，排序时会获得时效加分；
- 每日上限仍把已被替代的记忆计入当天条数；
- 导入数据的 ULID 时间和 note_date 可能不一致，因此分组内按 (note_date, id) 排序。
