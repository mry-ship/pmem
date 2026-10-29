---
id: 01M6408PE9YTBVGAGHYHKDC0QB
module: feature.Retrieval
entity: DumpRank
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_dump_pitfalls_first
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 无关键词速览防错类排前，默认名额内结论最多 2 条
verify: uv run pytest tests/index/test_index.py -k empty_query
applies: search 未带 query 且没有锚点命中当前 path；limit>5 不截非防错条数
---
用户要求：模块速览不要反复塞满从未被采用的结论，采用率偏低时先露出防错类。

必须保持：无关键词、无锚点命中（related 为空）时，本模块教训里 exclusion/risk/correction 排前；
默认 limit≤5 时非防错最多 2 条。
有关键词命中时名额内保持原排序，不按采用率调分，也不加相关度阈值。
祖先教训仍在本模块结果之外另给。

适用：search 未带 query、且当前 path 没有锚点命中。limit>5 的枚举或核对场景不截非防错条数。

入口：src/pmem/index/store.py#_dump_pitfalls_first
