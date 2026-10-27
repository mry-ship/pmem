---
id: 01M5YS67RKVEQV6Y3X6EBWSYKW
module: feature.Metrics
entity: Health
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#SearchOps.search
- src/pmem/metrics/health.py#_misses
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 检索事件只记教训 id，只返回功能记录时被算成落空
verify: 对只有 feature 的模块做一次成功检索，看事件日志的 ids 为空，pmem health 把该次算进检索落空
applies: 读 pmem health 的检索落空或返回次数时；模块里课题很少、功能记录很多时更明显
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
现象：一次检索若只返回功能记录（features）、教训（items）为空，pmem health 的“检索落空热点”仍会把它算成没查到。功能记录被返回的次数也不进入“返回却未写入”。
原因：SearchOps.search 写事件时 ids 只取 response.items，不包括 features。
health 的 _misses 把没有 ids 的成功检索当落空；
_hot_returns / report 的返回次数也读这个 ids。
MCP 闸门那边会从 items、features、timeline 抽 id，所以“查过没有”不受影响，只影响健康报告和收益报告。
证据：service/search.py search 的 _log；metrics/health.py _misses。
