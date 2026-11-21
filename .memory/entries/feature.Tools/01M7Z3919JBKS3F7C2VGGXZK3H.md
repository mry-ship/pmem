---
id: 01M7Z3919JBKS3F7C2VGGXZK3H
module: feature.Tools
entity: ReadingHint
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_needs_reading_hint
- src/pmem/service/search.py#_search
- src/pmem/service/search.py#_by_ids
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 阅读顺序只在过期、有前提或多条时给一次
verify: uv run pytest tests/test_quality_efficiency.py::test_reading_hint_waits_until_stale_applies_or_several_hits
  tests/test_quality_efficiency.py::test_field_hints_are_given_once_per_conversation
  -q
applies: 改 search_memory 的提示、排序或过滤时
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
需求来源：用户要求把已列的记忆阅读顺序写进检索短提示。
必须保持：reading_hint 只在结果里有 stale、applies，或至少两条时返回。
单条未过期且没有 applies 不返回，避免第一次无关检索把提示用掉。
每个对话只给一次，清空去重记录后再给；
没有对话 id 时每次都给。
文案用 stale=true，并写明不要把「规则需核实」当成锚点过期。
再看 applies；
多条冲突时先看有锚点、有 verify、来源不是 inference 的，其余仍要看，并写明不改变排序。
不据此过滤或重排。
入口：search_memory 的 reading_hint。pmem search --brief 也会打出这句。
