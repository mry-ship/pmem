---
id: 01M5CRK801SA5G0Z2QDZPXE388
module: feature.Tools
entity: SeenDedupe
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#SearchOps._hints_once
- src/pmem/server/app.py#build_server
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 检索结果的字段说明（*_hint）每个对话只给一次，压缩后再给
verify: uv run pytest tests/test_quality_efficiency.py -k once_per_conversation
aliases:
- 固定提示
- hint 去重
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求在功能不变的前提下精简提示。
必须保持：
1) search_memory 结果里的 seen_hint、features_hint、applies_hint、verify_hint 在同一对话里只给一次；
   记在对话内去重文件里（hint:<字段名>），上下文压缩时随去重记录一起清空，之后再给一次。
   没有对话 id 时每次都给。
2) 结果字段的含义不再写在规则里，search_memory 的工具说明也只指向 *_hint；字段写法集中在 record_memory 工具说明。
入口：service/search.py 的 search、server/app.py 的工具说明。
