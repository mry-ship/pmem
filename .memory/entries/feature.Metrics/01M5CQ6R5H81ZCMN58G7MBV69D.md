---
id: 01M5CQ6R5H81ZCMN58G7MBV69D
module: feature.Metrics
entity: Events
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/events.py#read_events
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 事件日志里不是对象的 JSON 行要跳过，report/health 不能因此崩溃
verify: uv run pytest tests/metrics/test_metrics.py -k not_objects
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，审查复现：events.jsonl 里有一行合法 JSON 但不是对象（如多进程写坏后剩下的 123）时，read_events 对它调 .get 抛 AttributeError，pmem report 和 pmem health 整个崩溃。
必须保持：read_events 只产出 JSON 对象，解析失败的行和非对象的行都跳过，旧日志里的坏行无需清理。
入口：metrics/events.py 的 read_events。
