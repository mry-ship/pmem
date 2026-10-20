---
id: 01M5CAVT4PAMCKKMG8X5ZTDMWQ
module: feature.Onboarding
entity: Rule
kind: feature
status: active
supersedes:
- 01M5ACNTYN6MXKZ8KBSCG7S5HS
anchors:
- src/pmem/generate/templates.py
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 规则模板讲两层写法，合并技能不合并适用条件不同的记忆
aliases:
- 规则
- pmem.mdc
- 合并技能
- 有教训才写
---
用户要求（2026-10-19）：pmem init 生成的规则要讲清两层写法，合并技能不能把不同前提的记忆合并。
必须保持：规则“何时写”分功能记录（改了模块就写，只改测试、生成代码、配置或行为没变时不写）和教训（有才写）两层；
“用之前核对”说明 features 只给标题、改动前用 ids 取全文、applies 先自检。
pmem-compact 技能：适用条件不同的记忆不合并，功能记录和教训不合并到一条。
已接入项目要重新运行 pmem init 才拿到新规则。
入口：generate/templates.py 的 RULE_BODY、COMPACT_SKILL。
