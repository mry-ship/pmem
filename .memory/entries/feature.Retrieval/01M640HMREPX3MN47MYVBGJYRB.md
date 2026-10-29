---
id: 01M640HMREPX3MN47MYVBGJYRB
module: feature.Retrieval
entity: DumpPitfalls
kind: feature
status: active
supersedes:
- 01M6408PE9YTBVGAGHYHKDC0QB
anchors:
- src/pmem/index/store.py#_dump_pitfalls_first
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 无关键词的模块速览防错类排前，非防错默认最多 2 条
verify: uv run pytest tests/index/test_index.py -k empty_query_prefers_pitfalls
applies: 模块速览（无 query、无锚点命中）；有关键词时不适用
aliases:
- 模块速览
- 防错优先
---
需求来源：2026-10-29 FixOrder：模块检索常把热门结论塞满默认名额，防错类排不上，采用率被噪声拉低。
必须保持：无关键词、也无锚点命中（related 为空）的模块速览，先排 exclusion / risk / correction，默认 limit≤5 时非防错最多 2 条。
limit>5 时不截非防错。
有关键词或按文件锚点命中时不要调用这套重排，名额内保持原排序（见 SpreadBatches 01M5CSD7D15G1NFSH0CZ1S4DW4）。
入口：src/pmem/index/store.py _dump_pitfalls_first、DUMP_OTHER_MAX。
加分 +0.05 仍只给 BOOSTED_KINDS（01M5Y5ACB21WS689TCHATJBRQC），本条不改加分。
