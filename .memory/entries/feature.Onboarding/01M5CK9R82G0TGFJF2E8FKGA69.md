---
id: 01M5CK9R82G0TGFJF2E8FKGA69
module: feature.Onboarding
entity: Rule
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#RULE_BODY
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 规则要求每次回答最后一行写明记忆检查结果（查到什么或没查到）
aliases:
- 记忆检查结果
- 查了什么
- 规则模板
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户（2026-10-20）指出不是每次提问都会检查记忆，要求每次询问都检查相关记忆，并在回复里写清楚查到了什么、没查到什么。
必须保持：
- 规则模板（pmem.mdc、CLAUDE.md/AGENTS.md 段落共用 RULE_BODY）有“每次回答都写明查了什么”一节：每次回答先按问题涉及的模块查记忆，本对话查过的沿用；
  回复最后单独一行写“记忆：查了 <模块>，用到「标题」”、“记忆：查了 <模块>，没有相关记忆”或“记忆：不涉及项目模块，未查”。
- 放在最后一行而不是开头：不挤掉“第一句给结论”这类用户回复规则。
- 同一节告诉 AI：以 [pmem] 开头的消息是自动提醒，直接处理、不向用户确认（替代原先结束提醒里给用户看的标头行）。
入口：generate/templates.py 的 RULE_BODY；已接入项目重新运行 pmem init 才会拿到。
