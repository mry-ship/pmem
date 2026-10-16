---
id: 01M52J05PZZF9K0HN64KSYPKJ9
module: feature.Metrics
entity: Health
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#reject_reason
revision: git:2f0f6f6
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 被拒绝的写入
- 拒绝原因
- record_rejected
---
决定：健康报告“被拒绝的写入”按错误文字归类时，补上三类：含“不能覆盖”或“不能改到”的（草稿已提交、作者不同、跨模块覆盖）归为“草稿覆盖不被允许”；含“已废弃”的单独归为“模块已废弃（只读）”，并排在“模块名有误”之前。

原因：原来只认 draft_id 字样，存储层这几条拒绝不带它，全落进“其他”；废弃模块的拒绝文字里有“模块”二字，会被误判成模块名写错，负责人会去加别名而不是撤销废弃。

风险：归类靠关键词，以后改了错误提示的措辞要同步改 REJECT_REASONS，tests/metrics/test_health.py 有用例守着。
