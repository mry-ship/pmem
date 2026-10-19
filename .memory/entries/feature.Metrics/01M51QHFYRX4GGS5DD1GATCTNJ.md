---
id: 01M51QHFYRX4GGS5DD1GATCTNJ
module: feature.Metrics
entity: Report
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#build_report
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 收益报告
- 建议错误
verified: '2026-10-19'
---
根因：收益报告在“只查不写的分析型对话”较多时，总是建议“打开 gate.analysis_reminder”，但该开关默认已经开启，建议是错的。原因是报告没有读取当前配置。

处理：生成报告时读取 gate.analysis_reminder 的实际值并写入习惯统计；只有存在“查过但没写”的对话、且提醒未开启时才给这条建议。已用测试覆盖开启和关闭两种情况。
