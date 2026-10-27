---
id: 01M5Y5RK22FT59S9AZCCZGND9F
module: feature.Onboarding
entity: Templates
kind: feature
status: active
supersedes:
- 01M5Y51NXWN2PBNAN7EMR8JS15
anchors:
- src/pmem/generate/templates.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 新项目 config 模板里 analysis_reminder 默认 false
verify: 'rg "analysis_reminder: false" src/pmem/generate/templates.py'
applies: pmem init 尚无 config.yaml 时
verified: '2026-10-27'
verified_at: '2026-10-27T17:33:08.864+08:00'
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
需求来源：与 Gate AnalysisReminder 缺省关对齐，避免新项目一接入就弹查阅/排查 followup。
必须保持：pmem init 生成的 config.yaml 模板写 analysis_reminder: false，注释说明默认关因打断阅读、需要时改 true（排查类与纯查阅都会催）。
已有项目的 config.yaml 不被 init 覆盖。
不替代同议题关于 spec.reminder 缺省 false 的功能记录。
入口：src/pmem/generate/templates.py。
