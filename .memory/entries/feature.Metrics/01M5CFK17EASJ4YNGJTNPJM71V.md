---
id: 01M5CFK17EASJ4YNGJTNPJM71V
module: feature.Metrics
entity: Report
kind: correction
status: active
supersedes:
- 01M51QHFYRX4GGS5DD1GATCTNJ
anchors:
- src/pmem/metrics/report.py#build_report
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 收益报告按实际配置判断是否建议打开 analysis_reminder；只测了开启情况
aliases:
- 收益报告
- 建议错误
---
根因：收益报告在“只查不写的分析型对话”较多时总是建议“打开 gate.analysis_reminder”，但该开关默认已开，建议是错的，因为报告没读当前配置。
处理：生成报告时读取实际配置，提醒实际生效要求 analysis_reminder 为真且 gate.mode 不是 off；只有存在“查过但没写”的对话、且提醒未生效时才给这条建议。
更正：旧记忆说“已用测试覆盖开启和关闭两种情况”，实际只测了开启（tests/metrics/test_metrics.py），关闭情况没有用例。
