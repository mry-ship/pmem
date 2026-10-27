---
id: 01M5YBA1WH9XTFR2097AC7N57R
module: feature.Onboarding
entity: Rule
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#RULE_BODY
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: RULE_BODY 约 1379 字，守 1400 上限与必含短语单测
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
需求来源：2026-10-27 CI 单测 test_trimmed_rule 要求 len(RULE_BODY)<1400 且含固定短语列表。
必须保持：增删规则措辞时同步 .cursor/rules/pmem.mdc；超长先压缩表述，不随意抬高上限。
适用：pmem init 生成的 RULE_BODY 与 alwaysApply 规则。
入口：src/pmem/generate/templates.py 的 RULE_BODY；
tests/test_feature_records.py::test_trimmed_rule_keeps_every_instruction_that_changes_behaviour。
