---
id: 01M5CAW1M1MTHEDY85BKFFSB6N
module: feature.Metrics
entity: FeatureCoverage
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_feature_coverage
- src/pmem/metrics/report.py#_pitfall_share
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 报告加功能记录覆盖率，防错类占比只算教训
verify: pmem report 输出里有 功能记录覆盖 一行；pytest tests/test_feature_records.py
aliases:
- 覆盖率
- 功能记录
- 防错类占比
---
用户要求（2026-10-19）：要能看出功能记录有没有记全，防错类占比不能被功能记录稀释。
必须保持：pmem report 的防错类占比只在教训（LESSON_KINDS）里算；
新增“功能记录覆盖”：stop 事件 required 里的模块，同一对话（source_conversation 相同，或对话期间首尾各放宽 60 秒内本机新写）有同模块 feature 的比例，目标不低于 80%。
旧日志没有 required 字段的不计入。
入口：metrics/report.py 的 _pitfall_share、_feature_coverage、_render_quality。
