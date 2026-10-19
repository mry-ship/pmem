---
id: 01M5A1JECRPPWGZSH9FBEV2NQ7
module: infra.Model
entity: Ulid
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/ids.py#ulid_ms
revision: git:501a142
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- ULID 时间
- 生成时间
- ulid_ms
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：从 ULID 取生成时间的 ulid_ms 从 index/store.py 移到 core/ids.py，和生成、校验放在一起。
原因：收益报告（metrics/report.py）和导入测试只为这一个小函数导入检索索引模块，连带加载 numpy，也让报告对索引多了一条不必要的依赖。
影响：行为不变；index/store.py 改为从 core.ids 导入，全量测试通过。以后用到 ULID 时间的代码都从 core.ids 取。
