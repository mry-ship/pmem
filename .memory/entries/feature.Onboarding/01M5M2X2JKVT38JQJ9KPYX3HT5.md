---
id: 01M5M2X2JKVT38JQJ9KPYX3HT5
module: feature.Onboarding
entity: Templates
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:6096f71
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 新项目配置模板里 spec.reminder 是 false
applies: pmem init 在还没有 config.yaml 时生成配置
aliases:
- 规格提醒
- spec.reminder
verified: '2026-10-27'
verified_at: '2026-10-27T17:33:08.864+08:00'
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户要求：规格提醒默认关闭，接入后无感。
必须保持：pmem init 新建的 config.yaml 模板里 spec.reminder 为 false。已有 config.yaml 不覆盖。
入口：generate/templates.py 的 CONFIG_TEMPLATE。
