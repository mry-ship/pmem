---
id: 01M5EJPP5YKB4M6FCESZ47CCXR
module: feature.Onboarding
entity: Rule
kind: feature
status: active
supersedes:
- 01M5CAVT4PAMCKKMG8X5ZTDMWQ
- 01M5CK9R82G0TGFJF2E8FKGA69
- 01M5CVNA2AZGWRB09Z1K36DXDZ
anchors:
- src/pmem/generate/templates.py
- src/pmem/generate/templates.py#RULE_BODY
- src/pmem/generate/templates.py#CONSOLIDATE_SKILL
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 生成规则 RULE_BODY 约 1200 字：两层写法、回复末行写查了什么、技能合并约束
applies: pmem init 生成的规则和技能；已接入项目需重跑 pmem init
---
需求来源：用户 2026-10-19～20 要求规则讲清两层写法、每次回答都检查记忆并写明查了什么，以及在功能不变的前提下精简规则。
必须保持：
1) RULE_BODY（pmem.mdc、CLAUDE.md/AGENTS.md 的 pmem 段落共用）约 1200 字，只说：何时查、何时写、回复末行的检查结果、[pmem] 提醒直接处理、跳过记忆、工具不可用时改用终端、stale 和种子记忆先对照代码、改动影响功能记录时先用 ids 取全文。
   字段写法在 record_memory 说明里。
   test_trimmed_rule_keeps_every_instruction_that_changes_behaviour 锁定这些句子和长度上限。
2) “何时写”分两层：功能记录（改了模块就写；只改测试、生成代码、配置或行为没变时不写）和教训（有才写）。
3) “每次回答都写明查了什么”：本对话查过的模块沿用；
   回复最后单独一行写“记忆：查了 <模块>，用到「标题」”“记忆：查了 <模块>，没有相关记忆”或“记忆：不涉及项目模块，未查”。
   放最后一行而不是开头，不挤掉“第一句给结论”这类用户规则。
   以 [pmem] 开头的消息是自动提醒，直接处理、不向用户确认。
4) 种子记忆不写“成立就 confirm_memory”：confirm 只刷新核对日期，转正要负责人 pmem seed --accept。
5) pmem-compact 技能：适用条件不同的记忆不合并，功能记录和教训不合并到一条。
   pmem-consolidate 技能读矛盾的两条用 pmem search --id，不用 --entity（同一对话给过的会折叠成标题）；
   按议题拆模块的示例带 --to。
入口：generate/templates.py 的 RULE_BODY、COMPACT_SKILL、CONSOLIDATE_SKILL；已接入项目要重新运行 pmem init 才拿到新规则。合并自 3 条功能记录。
