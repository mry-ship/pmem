---
id: 01M5Y51NXWN2PBNAN7EMR8JS15
module: feature.Onboarding
entity: Templates
kind: feature
status: active
anchors:
- src/pmem/generate/templates.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: config 模板里 analysis_reminder 注释写明排查收口与防错类
verify: rg analysis_reminder src/pmem/generate/templates.py
applies: pmem init 尚无 config.yaml 时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：与 Gate AnalysisWrap 同步，避免注释仍写成「只查不改才提醒一次」。
必须保持：pmem init 生成的 config.yaml 模板中 analysis_reminder 注释说明排查类查过未落结论时催防错类，以及纯查阅场景也会提醒。已有项目的 config.yaml 不被 init 覆盖。
不替代同议题关于 spec.reminder 缺省 false 的功能记录。
入口：src/pmem/generate/templates.py。
