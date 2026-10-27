---
id: 01M5Y5XVHSTH4W6T5C93QTFJ7K
module: feature.Gate
entity: AnalysisWrap
kind: correction
status: active
supersedes:
- 01M5Y5QNC6X4YCTFNS24VDNAHB
anchors:
- src/pmem/core/config.py
- src/pmem/generate/templates.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 用户确认：analysis_reminder 产品默认关，优先不打断阅读
verify: src/pmem/core/config.py DEFAULTS analysis_reminder 为 False；templates 与手册为
  false
applies: 改 analysis_reminder 默认或想把默认扳回 true 时
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
更正：排除项「为少打扰就把 analysis_reminder 默认改 false」已不成立。
用户 2026-10-27 明确要求产品默认也关掉，理由是 Cursor 展示的结束 followup 很影响阅读内容；项目级 config 关掉不够，未写该项的升级项目仍会弹。
取舍：收口缺口与防错类占比仍靠显式打开 gate.analysis_reminder、规则【pmem】自检与 report 建议；不再用默认 followup 强迫催写。
处理：DEFAULTS / init 模板 / 手册示例均为 false；需要催写的项目自行改 true。勿再把默认扳回 true。
