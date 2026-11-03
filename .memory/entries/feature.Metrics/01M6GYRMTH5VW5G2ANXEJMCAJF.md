---
id: 01M6GYRMTH5VW5G2ANXEJMCAJF
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py
revision: git:a6de816
author: 1002378395@qq.com
note_date: '2026-11-03'
summary: bench on 组 MCP 改为 pmemw serve
verify: tests/bench/test_bench.py 仍通过
applies: pmem bench on 组
---
需求来源：与接入模板一致，Windows 对照实验也不应弹控制台。
必须保持：on 组仍注入 pmem MCP、规则前缀与 .memory 复制；
仅 command 从 pmem 改为 pmemw。
入口：src/pmem/bench/runner.py。
