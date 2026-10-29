---
id: 01M640GJ99KCTH0F0V4FYPKHJ7
module: feature.Tools
entity: SeenFill
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_collapse_seen
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 同一对话再查先给未见全文，已见标题不占满名额
verify: uv run pytest tests/test_quality_efficiency.py -k unseen_before_collapsed
applies: 带 source_conversation 且带 query 或 path，本对话已返回过全文
---
用户要求：同一对话反复检索同一模块时，已给过全文的标题不能占满名额，后面的记忆还要出得来。

必须保持：同一对话再查且带了 query 或 path 时，内部多取一页（不超过 MAX_LIMIT），先排未见全文的，再补已见标题，截回原 limit；
已见仍只给标题，full=true 仍给全文。
无 query 的模块速览不扩页。
不按采用率排序。

适用：search_memory 带 source_conversation，且本对话 already 返回过全文。

入口：src/pmem/service/search.py#_collapse_seen
