---
id: 01M5Y5RFP6VJJ7WDBDT38XKM7F
module: feature.Gate
entity: AnalysisWrap
kind: feature
status: active
supersedes:
- 01M5Y51BQTZ6E2PH43N5MAGHVH
anchors:
- src/pmem/core/config.py
- src/pmem/hooks/reminders.py
- src/pmem/generate/templates.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: analysis_reminder 缺省关；开启后排查/查阅缺口仍催防错类
verify: uv run pytest tests/hooks/test_gate.py -k "consulted or analysis_gap or analysis_reminder"
applies: 回合结束判断要不要发查阅/排查催写时
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
需求来源：用户要求结束催写默认关掉，followup 很影响阅读。
必须保持：
1) gate.analysis_reminder 缺省 false；DEFAULTS、init 模板、手册示例一致。
2) 显式 true 时仍保持：排查类查过未写的模块结束催防错类（改过别的模块也不豁免）；非排查整段只查不改不写走较软查阅提醒；【pmem…】声明无新结论不催。
3) stop_reminder 缺省仍为 true（本项只关 analysis）。
入口：core/config.py DEFAULTS；hooks/reminders.py；generate/templates.py。
