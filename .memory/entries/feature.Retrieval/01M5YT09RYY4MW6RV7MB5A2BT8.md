---
id: 01M5YT09RYY4MW6RV7MB5A2BT8
module: feature.Retrieval
entity: Supersede
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/graph.py#current_entries
- src/pmem/index/graph.py#load_replaced_ids
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: current_entries 可并入全库替代目标，单目录也能藏起外模块替代
verify: uv run pytest tests/index/test_graph.py::test_digest_prefers_exclusions_and_caps_each_topic
applies: 调用方只拿到一个模块目录里的记忆时；传入的集合必须来自 Entry.replaces
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
需求来源：摘要要和检索用同一套替代关系，但 Hook 不能为此加载整个检索。
必须保持：current_entries、digest、file_features、project_pitfalls 接受可选的 replaced（这批文件之外仍生效的替代目标）。
不传时行为与以前一致，只看本批的 Entry.replaces。
load_replaced_ids 扫全部记忆文件，只收集 replaces()，撤销的合并不产生替代，解析失败的文件跳过。
适用：计算“现行”时。检索索引自己扫全库，不用这个参数。
