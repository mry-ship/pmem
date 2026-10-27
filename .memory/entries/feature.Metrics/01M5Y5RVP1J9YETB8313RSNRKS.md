---
id: 01M5Y5RVP1J9YETB8313RSNRKS
module: feature.Metrics
entity: Report
kind: conclusion
status: active
supersedes:
- 01M5CFK17EASJ4YNGJTNPJM71V
- 01M51QHFYRX4GGS5DD1GATCTNJ
anchors:
- src/pmem/metrics/report.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: analysis_reminder 缺省关；有 analysis_left 时报告建议打开
verify: uv run pytest tests/metrics/test_metrics.py::test_analysis_conversations_are_reported
applies: 解读 pmem report 习惯节或改 analysis_reminder 建议文案时
source:
  conversation: 519d8eba-5c64-4862-a68d-83aecb454824
---
更正报告习惯节与 analysis_reminder 缺省的关系：该开关产品缺省现为 false。
仍成立：生成报告时读实际配置；
提醒生效要求 analysis_reminder 为真且 gate.mode 不是 off；
只有存在「查过但没写」的对话（analysis_left）且提醒未生效时才建议「打开 gate.analysis_reminder」。
测试：tests/metrics/test_metrics.py::test_analysis_conversations_are_reported 覆盖默认关并出现建议的情况。
其余统计口径（新写记忆数文件、检索前后 30 秒关联、提醒转化来源、对话内重复按压缩切分等）仍以同议题既有结论为准，本条只收口默认值与建议文案。
