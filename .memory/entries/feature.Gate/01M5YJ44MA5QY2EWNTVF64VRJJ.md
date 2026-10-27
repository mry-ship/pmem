---
id: 01M5YJ44MA5QY2EWNTVF64VRJJ
module: feature.Gate
entity: AnalysisReminder
kind: correction
status: active
supersedes:
- 01M5Y5RB6QS7DWBWFH6044VA1D
anchors:
- src/pmem/core/config.py
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: analysis_reminder 缺省关；本仓库靠 DEFAULTS，config 不再显式写 false
verify: DEFAULTS 与 templates 为 false；本仓库 config.yaml 无 analysis_reminder 键；uv run
  pytest tests/hooks/test_gate.py -k analysis_reminder_defaults_off
applies: 未在 config.yaml 显式写 analysis_reminder 的项目
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
更正：gate.analysis_reminder 产品缺省为 false（DEFAULTS、init 模板、手册）。Cursor 会把 stop followup 显示给用户，默认关避免打断阅读。
已接入项目：config 未写该项的升级后不再弹查阅/排查催写；已写成 true 的仍提醒。
本仓库 .memory/config.yaml 不显式写 analysis_reminder，与未写该项的项目一样走 DEFAULTS。
推翻「默认开」的旧决定。
