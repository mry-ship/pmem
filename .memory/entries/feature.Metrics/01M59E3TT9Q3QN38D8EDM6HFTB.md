---
id: 01M59E3TT9Q3QN38D8EDM6HFTB
module: feature.Metrics
entity: Health
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#build_health
- src/pmem/metrics/health.py#render
revision: git:21d24e9
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 服务重启
- 看门狗
---
决定：健康报告新增“MCP 服务被看门狗重启（N 次）”一节，按原因汇总本机 server_restart 事件，只算崩溃（crash）和超时（timeout），代码更新导致的重载（reload）是正常行为不计。
偶发可忽略；
反复崩溃要看 Cursor 的 MCP 日志，反复超时可调大 server.request_timeout。
原因文字里带返回码和方法名，同类问题可能分成几行。
