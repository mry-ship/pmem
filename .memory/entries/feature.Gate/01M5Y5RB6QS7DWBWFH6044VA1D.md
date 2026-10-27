---
id: 01M5Y5RB6QS7DWBWFH6044VA1D
module: feature.Gate
entity: AnalysisReminder
kind: correction
status: active
supersedes:
- 01M4ZD0C7VYS755CHE1TKQ82M9
- 01M59KGHXJSZG6ZPT1GRAXPZAN
- 01M51P2FW5SRCZRHV2W02NGE0J
- 01M51VMYMTTEC3T8HFRCX3ZTDW
- 01M5Y5XVHSTH4W6T5C93QTFJ7K
anchors:
- src/pmem/core/config.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: analysis_reminder 缺省改为关，避免结束 followup 打断用户阅读
verify: DEFAULTS 与 templates 为 false；uv run pytest tests/hooks/test_gate.py -k analysis_reminder_defaults_off
applies: 未在 config.yaml 显式写 analysis_reminder 的项目
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
更正：gate.analysis_reminder 产品缺省由 true 改为 false。
原因：Cursor 会把 stop 的 followup_message 显示给用户，排查/纯查阅催写虽是给 Agent 的，仍打断阅读；与 spec.reminder 缺省关同一理由。
仍成立：设为 true 且闸门非 off 时，排查类查过未写、或整段只查不改不写，仍按 AnalysisWrap 催防错类；回复【pmem…】声明无新结论不催；report 在有 analysis_left 且提醒未生效时建议打开该开关。
已接入项目：config 未写该项的升级后不再弹；已写成 true 的仍提醒。本仓库 config 已显式 false。
推翻「默认开」的旧决定。同议题重复更正见 AnalysisWrap，以本条为默认值结论即可。
