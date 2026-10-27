---
id: 01M5YT0ZCMMGDQ37XDJRGWJ0RS
module: feature.Tools
entity: SearchLog
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#SearchOps.search
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 检索事件的 ids 含功能记录，只有功能记录不算检索落空
verify: uv run pytest tests/test_feature_records.py::test_search_event_counts_feature_ids_when_there_are_no_lessons
applies: 读 pmem health 的检索落空或返回次数、pmem report 的命中次数时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
需求来源：只返回功能记录、没有教训的成功检索，被健康报告算成没查到；功能记录被返回的次数也不进“返回却未写入”。
必须保持：search 事件的 ids 和 kinds 同时包含教训（items）和功能记录（features）。作者列表仍只来自教训，功能记录的标题行没有作者。闸门是否“查过”仍看 ok，不看这个 ids。
适用：MCP 和命令行的 search_memory 写事件时。
