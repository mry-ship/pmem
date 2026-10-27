---
id: 01M5YV5TGJVRQ3SEVDX166MWKR
module: feature.Metrics
entity: Quality
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_repeats
- src/pmem/service/search.py#SearchOps.search
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 对话内重复不把功能记录标题算成再次给出全文
verify: uv run pytest tests/test_quality_efficiency.py::test_repeats_ignore_feature_titles_that_share_the_search_event
applies: 读 pmem report 的对话内重复率时；search 事件的 ids 已经包含功能记录之后
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
更正：search 事件的 ids 开始同时记功能记录之后，对话内重复若按 ids 全部计入，会把只给过标题的功能记录和规划算成“给过全文又整条给了一遍”。
必须保持：这项的分子和分母只算教训。
kinds 与 ids 按下标一一对应，下标上是 feature 或 plan 的跳过。
没有 kinds 的旧日志仍按全部 id 计。
教训的重复、折叠、按压缩切分不变。
检索落空仍然把只有功能记录的成功检索算命中。
适用：读收益报告的对话内重复率。
