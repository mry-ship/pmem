---
id: 01M7WFXW6Z5X4GSZH43PBJVN1W
module: feature.Retrieval
entity: StaleCache
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_cached
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 结论：同一 AnchorChecker 实例改代码后再核对会命中短缓存漏报过期
verify: uv run pytest tests/index/test_anchors.py -k enforced_by
applies: 单测或同进程内连续核对、中间又改了锚点/规则文件时
---
结论：同一 AnchorChecker 实例里，_cached 对 changed_since 有短时内存缓存（CHANGE_CACHE_SECONDS）。
先核对「改前」、再改文件、再用同一实例核对「改后」，会命中改前的空结果，漏报需核实。
测 enforced_by 规则文件变更时已踩到。
处理：改代码前后各 new 一个 AnchorChecker；
生产路径每次 Hook/进程通常是新实例，一般无妨。
不要据此关掉缓存——跨调用重复 git 会慢。
