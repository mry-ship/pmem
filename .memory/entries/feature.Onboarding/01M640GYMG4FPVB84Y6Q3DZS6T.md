---
id: 01M640GYMG4FPVB84Y6Q3DZS6T
module: feature.Onboarding
entity: Skills
kind: feature
status: active
supersedes:
- 01M640JGCXTRZYDQMG3XV50JG7
anchors:
- src/pmem/generate/templates.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: compact 技能合并时保留 exclusion/risk/correction，不收成 conclusion
verify: uv run pytest tests/test_feature_records.py -k compact_skill
applies: 生成或更新 pmem-compact 技能时
aliases:
- compact技能
- 防错kind
---
需求来源：2026-10-29 FixOrder：已接入项目按 pmem-compact 合并时，不要把 exclusion / risk / correction 收成 conclusion。
必须保持：pmem init 生成的 compact 技能正文写明三类防错 kind 合并后保持，其余用 conclusion 或 decision。已接入项目要重跑 init 或同步技能文件才会拿到新文案。
适用：生成或更新 pmem-compact 技能模板时。
入口：src/pmem/generate/templates.py COMPACT_SKILL。
花括号规则不变：模板经 str.format，正文花括号必须写成 {{ }}（见 TemplateBraces）。
