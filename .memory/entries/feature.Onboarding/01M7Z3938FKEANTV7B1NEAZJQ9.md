---
id: 01M7Z3938FKEANTV7B1NEAZJQ9
module: feature.Onboarding
entity: ReviewStates
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: pmem-review 四态要逐条写出，排除项和决定仍要摘
verify: uv run pytest tests/test_integrations.py::test_quality_templates_format_and_keep_frozen_triggers
  -q
applies: 改 pmem-review 或 init 写出的审查技能时
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
需求来源：用户要求 pmem-review 按四态逐项核对规格。
必须保持：检查第 1 步从规格、排除项、决定和功能记录摘出必须保持的行为，并列出未触及、符合、违反、待核实。
输出要逐条一行状态；
违反和待核实写路径与证据，未触及和符合不展开。
字段名和须按字面抄的原文用 pmem spec closed。
行为是否仍成立由审查判断。
带「待对照代码核对」的预填不能标成违反。
不自动改规格。
记忆阅读顺序不写进本技能、pmem-minimal、pmem-quality 和 RULE_BODY。
入口：templates.py 的 REVIEW_SKILL。pmem init 写到 Cursor、Claude、Codex 的 skills/pmem-review。
