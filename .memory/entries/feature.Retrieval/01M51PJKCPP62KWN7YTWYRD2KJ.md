---
id: 01M51PJKCPP62KWN7YTWYRD2KJ
module: feature.Retrieval
entity: Verify
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py
- src/pmem/index/store.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 过期
- stale
- 需核实
---
决定：“记忆是否过期”的判断（锚点文件已删、找不到符号、核对基准日之后又改过）从 MemoryIndex 中抽出为独立的 AnchorChecker（src/pmem/index/anchors.py）。检索、memory_graph、读代码摘要、改代码拦截和 Wiki 共用这一套，规则不变：7 天内提交的记忆以提交日为基准；改动日期批量查询，结果缓存 60 秒。

原因：之前只有 search_memory 会标 stale。读代码摘要、模块全貌和 Wiki 都展示同样的结论，却看不出已过期，Agent 可能直接照着过期的坑或方案行事。Hook 进程不加载索引，所以检查器只依赖项目根目录和版本库。

代价：Hook 中每次给出摘要或拦截时，要跑一次 git log 加一次 git diff（SVN 是 info 加 status）。每个模块每个对话最多两次，本仓库实测在百毫秒以内。全量 Wiki（38 条现行记忆）约 0.8 秒。SVN 大仓库首次查询可能更慢，需要观察。
