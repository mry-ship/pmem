---
id: 01M7WGXMVQ4WYADH47M1MYXVHQ
module: feature.Retrieval
entity: WhenFacets
kind: exclusion
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 排除：when 不匹配只降权、仍返回冲突条目
verify: uv run pytest tests/core/test_facets.py -k conflicts
applies: 改 search 过滤或讨论 when 语义时
---
排除：把「检索 when 不匹配」做成只降权、仍返回冲突条目。

设计已定：明确冲突才排除，没写 when 的照常返回。只降权会让跨平台互斥结论混进结果，调用方仍可能套用错误平台的坑。

适用：改 search 过滤或讨论 when 语义时。
验证：uv run pytest tests/core/test_facets.py -k conflicts
