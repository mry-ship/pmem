---
id: 01M6JKMACSHVEF54SZJR4CKDXD
module: feature.Metrics
entity: Bench
kind: correction
status: active
supersedes:
- 01M6GYRMTH5VW5G2ANXEJMCAJF
anchors:
- src/pmem/bench/runner.py
revision: git:e51a54a
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: bench on 组 MCP 改回 pmem serve
verify: src/pmem/bench/runner.py command 为 pmem
applies: pmem bench on 组
---
更正：曾把 bench on 组 MCP command 改成 pmemw 以避黑框。与产品一致：MCP 必须用 pmem，避免 Windows stdio 被掐断。bench runner 已改回 pmem。
