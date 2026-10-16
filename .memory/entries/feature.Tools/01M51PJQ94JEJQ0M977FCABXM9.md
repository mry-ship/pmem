---
id: 01M51PJQ94JEJQ0M977FCABXM9
module: feature.Tools
entity: Graph
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- memory_graph
- stale
- 自动生成Wiki
---
决定：
- memory_graph 的模块全貌（topics[].latest）和议题时间线里的现行记忆，与检索用同一口径标 stale/check；有过期项时附 verify_hint。
- record 和 confirm 成功后自动重新生成 Wiki（wiki.auto，默认开，写到 wiki.dir）。生成失败只在返回的 warnings 里附一句，不影响写入本身。

原因：Wiki 是给人看的派生视图，靠人记得手动运行 pmem wiki 就会过时。确认记忆会改变“需核实”状态，所以 confirm 之后也要重新生成。

代价：每次写入多花约 1 秒（本仓库 38 条记忆实测 0.8 秒，含一次全量锚点核对）。记忆量很大的项目觉得慢，可以设 wiki.auto: false，改为手动 pmem wiki。
