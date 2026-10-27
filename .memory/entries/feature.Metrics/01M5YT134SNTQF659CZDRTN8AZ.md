---
id: 01M5YT134SNTQF659CZDRTN8AZ
module: feature.Metrics
entity: Health
kind: correction
status: active
supersedes:
- 01M5YS67RKVEQV6Y3X6EBWSYKW
anchors:
- src/pmem/service/search.py#SearchOps.search
- src/pmem/metrics/health.py#_misses
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 只返回功能记录的检索不再算检索落空
verify: uv run pytest tests/test_feature_records.py::test_search_event_counts_feature_ids_when_there_are_no_lessons
applies: 读 pmem health 的检索落空或返回却未写入次数时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
更正：只返回功能记录的成功检索不再被算成检索落空，功能记录的 id 也进入返回次数。
原因 search 事件的 ids 只取教训 items。现在 ids 和 kinds 同时包含 features。health 的落空判断仍是“成功且 ids 为空”，不用改健康报告本身。
