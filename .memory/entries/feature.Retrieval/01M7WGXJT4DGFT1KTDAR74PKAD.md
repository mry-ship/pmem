---
id: 01M7WGXJT4DGFT1KTDAR74PKAD
module: feature.Retrieval
entity: WhenFacets
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 检索可按 when 排除明确冲突的记忆
verify: uv run pytest tests/core/test_facets.py -k filter
applies: 改 when 过滤或 search 参数时
---
需求来源：v0.7 设计稿 §3.3。

必须保持：
- search_memory / pmem search 可传 when；明确冲突（同维度无交集）的记忆排除，没写 when 或没写该维度的保留。
- 结果出现 when 时附 when_hint；CLI --when 支持 platform=android 或 JSON；MCP record/search 同名参数。
- brief 输出「条件：维度=取值」。

入口：src/pmem/index/store.py、src/pmem/service/search.py、src/pmem/cli/main.py、src/pmem/server/app.py、src/pmem/cli/brief.py。
