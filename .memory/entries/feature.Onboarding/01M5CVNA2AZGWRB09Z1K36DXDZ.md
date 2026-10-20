---
id: 01M5CVNA2AZGWRB09Z1K36DXDZ
module: feature.Onboarding
entity: Rule
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#RULE_BODY
- src/pmem/generate/templates.py#CONSOLIDATE_SKILL
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 精简后的规则必须保留何时查写、末行检查、[pmem] 提醒、跳过记忆等要素，由测试锁定
verify: uv run pytest tests/test_feature_records.py -k trimmed_rule
aliases:
- 规则精简
- pmem.mdc
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求“在功能不变的前提下精简规则和提示”，之后又要求恢复被回退的精简并修复复查问题。
必须保持：
1) RULE_BODY（pmem.mdc、CLAUDE.md/AGENTS.md 的 pmem 段落）约 1200 字，只说何时查、何时写、回复末行的检查结果、[pmem] 提醒直接处理、跳过记忆、工具不可用时改用终端、stale 和种子记忆先对照代码、改动影响功能记录时先取全文；
   字段写法在 record_memory 说明里。
   test_trimmed_rule_keeps_every_instruction_that_changes_behaviour 锁定这些句子和长度上限。
2) 种子记忆不写“成立就 confirm_memory”：confirm 只刷新核对日期，转正要负责人 pmem seed --accept。
3) pmem-consolidate 技能读矛盾的两条用 pmem search --id，不用 --entity（同一对话里给过的会折叠成标题）；按议题拆模块的示例带 --to。
入口：generate/templates.py RULE_BODY / CONSOLIDATE_SKILL，改完跑 pmem init 更新本仓库的规则和技能。
