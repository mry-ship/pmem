---
id: 01M640KE7EFCXD6VH1VEMJMJX1
module: feature.Tools
entity: SeenDedupe
kind: exclusion
status: active
supersedes:
- 01M640H1ZXTWCRX6G7CCDFP6C4
anchors:
- src/pmem/service/search.py#search
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 无 query 的检索不要为去重扩页
verify: uv run pytest tests/test_quality_efficiency.py::test_path_only_second_search_does_not_undo_dump_cap
applies: 无 query 的检索，含只带 path 且没有锚点命中
aliases:
- 去重扩页
- 模块速览
---
排除：对话内去重扩页不要用在无 query 的检索，包括只带 path、没有锚点命中的模块速览。
无关键词时多取一页会把 DUMP_OTHER_MAX 截掉的结论又填回默认名额，模块速览的「防错优先、结论最多 2 条」失效。
只在有 query、且本对话已给过全文时扩页。
