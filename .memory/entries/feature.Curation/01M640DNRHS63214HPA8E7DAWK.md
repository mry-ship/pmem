---
id: 01M640DNRHS63214HPA8E7DAWK
module: feature.Curation
entity: WriteHints
kind: feature
status: active
supersedes:
- 01M640J8PC2W4NZ0CAMNPWWHMJ
anchors:
- src/pmem/core/quality.py#content_hints
- src/pmem/generate/templates.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 正文像排除项却写成结论时提示改 exclusion；合并时防错 kind 保持
verify: uv run pytest tests/core/test_quality.py::test_exclusion_shaped_conclusion_or_decision_is_hinted
applies: 写入 conclusion/decision 或按 pmem-compact 合并时
aliases:
- 防错kind
- compact默认
---
需求来源：2026-10-29 FixOrder（01M63YZWK9P6GQWNNWQKPSEQPG）：compact 默认 conclusion 会把防错收成普通结论，正文含「不要」时要提示改 kind，才能把 15 天防错占比稳住在 30% 以上。
必须保持：
1) conclusion / decision 去掉「决定/结论」标签后，正文开头是「排除」「不要」「别再/别去/别用」「禁止」时，写入提示改用 exclusion；
   本身已是 exclusion 的不再提示。
   「别人」这种只是「别」字开头的不算。
2) pmem-compact 技能：排除过的方向用 exclusion，风险用 risk，推翻旧结论用 correction；
   旧记忆已是这三类的，合并后保持，不要收成 conclusion。
   没有这类内容的仍用 conclusion 或 decision。
入口：src/pmem/core/quality.py content_hints；
src/pmem/generate/templates.py COMPACT_SKILL（已接入项目的 .cursor/skills/pmem-compact 与之一致）。
不替代功能记录检查需求来源的既有提示（01M5CAVRWPET8KQNB0ZSX1DGMA）。
