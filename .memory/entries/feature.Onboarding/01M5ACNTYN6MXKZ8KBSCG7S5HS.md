---
id: 01M5ACNTYN6MXKZ8KBSCG7S5HS
module: feature.Onboarding
entity: Templates
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 规则模板改为有教训才写；已接入项目需重跑 pmem init
aliases:
- 规则模板
- 有教训才写
- 何时写
---
决定（v0.3）：pmem init 生成的规则“何时写”改为“有教训才写”：被排除的方向、确认的根因或坑、看代码看不出的约束、方案取舍；
照常实现、没有教训的改动不写。
同时要求写一句话 summary，结论和更正写 verify，改哪里都会踩的坑加 scope: project。
“用之前核对”一节说明同一对话再查到只给标题、要全文带 full=true。
pmem-compact 技能合并时补 --summary / --verify。
风险：已接入的项目要重新运行 pmem init 才会拿到新规则，旧规则仍要求“每个模块写一条”，会继续产出变更记录。
