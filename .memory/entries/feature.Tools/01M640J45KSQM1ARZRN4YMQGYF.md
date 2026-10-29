---
id: 01M640J45KSQM1ARZRN4YMQGYF
module: feature.Tools
entity: SeenDedupe
kind: feature
status: active
supersedes:
- 01M640GJ99KCTH0F0V4FYPKHJ7
anchors:
- src/pmem/service/search.py#_collapse_seen
- src/pmem/service/search.py#search
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 同一对话再查时先给未见全文，已见标题不能占满名额
verify: uv run pytest tests/test_quality_efficiency.py::test_second_search_fills_limit_with_unseen_before_collapsed_titles
applies: 同一对话、非 full、带 query 的检索
aliases:
- 去重扩页
- 未见优先
---
需求来源：2026-10-29 FixOrder：对话内去重后，已见标题会占满默认 5 条，未见全文进不来，采用率分子加不上新记忆。
必须保持：同一对话、非 full、带 query、且已给过全文时，内部多取一页（不超过 MAX_LIMIT），折叠时先排未见全文再补已见标题，截回原 limit。
无 query 的模块速览（含只带 path、没有锚点命中）不扩页，避免冲掉检索侧对非防错条数的上限。
仍成立：已见只给标题，full=true 取全文（01M5ACNAPSVJZG4Y3F08N2YW89）。
入口：src/pmem/service/search.py SearchOps.search、_collapse_seen。
