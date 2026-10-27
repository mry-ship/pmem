---
id: 01M5Y5QNC6X4YCTFNS24VDNAHB
module: feature.Gate
entity: AnalysisWrap
kind: exclusion
status: active
anchors:
- src/pmem/core/config.py
- src/pmem/generate/templates.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 排除：为少打扰把 analysis_reminder 产品默认改成 false
verify: src/pmem/core/config.py DEFAULTS gate.analysis_reminder 为 True；templates 与手册示例为 true
applies: 想关排查结束提醒或改 analysis_reminder 默认值时
aliases:
- 关掉排查提醒
- analysis_reminder 默认
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
排除：因结束 followup 打断阅读，就把 gate.analysis_reminder 的产品默认（DEFAULTS / init 模板 / 手册）改成 false。
证据：本仓库与 TileMatch 的 analysis_left、防错类占比偏低，P0 正是靠默认开启的排查收口提醒催 exclusion；默认关掉等于产品侧放弃该杠杆。
处理：产品默认保持 true；仅本机嫌吵时在项目 .memory/config.yaml 写 analysis_reminder: false（可与 stop_reminder: false 并列），不要改 DEFAULTS。
2026-10-27 二次查漏曾发现默认被改 false 并改了手册/测试，已扳回。
