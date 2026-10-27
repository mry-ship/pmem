---
id: 01M5CVMP8TZEP8K6GMFAK15G8X
module: feature.Tools
entity: SeenDedupe
kind: feature
status: active
supersedes:
- 01M5CRK801SA5G0Z2QDZPXE388
anchors:
- src/pmem/service/search.py#SearchOps._hints_once
- src/pmem/server/app.py#build_server
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 字段说明类提示每个对话给一次；seen_hint 每次都给；工具说明写清 supersedes 用途
verify: uv run pytest tests/test_quality_efficiency.py -k once_per_conversation
verified: '2026-10-27'
verified_at: '2026-10-27T15:52:36.858+08:00'
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求在功能不变的前提下精简提示，复查后又要求全部修复。
必须保持：
1) features_hint、applies_hint、verify_hint 在同一对话里只给一次（记在对话内去重文件 hint:<字段名>），上下文压缩时随去重记录清空、再给一次；没有对话 id 时每次都给。
2) seen_hint 很短，又是终端用户知道“怎么取全文”的唯一途径（终端看不到工具说明），每次折叠都给。
3) record_memory 的工具说明是字段写法的唯一出处（规则不再重复）：supersedes 填本模块被推翻的旧结论、说同一件事的旧功能记录、已实现的规划；anchors 尽量写到函数。
入口：service/search.py _hints_once、server/app.py 的工具说明。
