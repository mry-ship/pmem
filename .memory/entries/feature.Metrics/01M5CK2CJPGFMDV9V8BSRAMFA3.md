---
id: 01M5CK2CJPGFMDV9V8BSRAMFA3
module: feature.Metrics
entity: Report
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_compactions
- src/pmem/metrics/report.py#_repeats
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 对话内重复率按上下文压缩切分，压缩后重发全文不算重复
verify: uv run pytest tests/test_quality_efficiency.py -k repeats
aliases:
- 对话内去重
- 重复返回
- 上下文压缩
- compact
---
需求来源：用户要求先补“压缩时记一条事件”并让报告按压缩切分统计，才能判断去重是否真正有效。
必须保持：
- pmem report 的对话内重复在每次压缩处重置“已给过全文”，压缩后再给全文是设计内行为，不算重复。
- 压缩优先取 Hook 记的 compact 事件；没有 compact 事件的旧对话按推断：同一对话同一模块再次出现读代码摘要（前一次带了记忆 id，或之前按模块检索过）就认为中间压缩过。
- 报告单列压缩次数、其中推断的次数，以及不扣除压缩时的重复条数和比例，便于和旧报告对照。
入口：metrics/report.py 的 _compactions、_repeats；compact 事件由 hooks/gate.py 的 on_compact 写。
