---
id: 01M5CGMVGQHC1CCJD0MFR9MK0Y
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py#run_bench
- src/pmem/bench/runner.py#BenchUnavailable
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: bench 一个用例失败不影响其他用例，只有缺 SDK 或 API Key 时中止
verify: uv run pytest tests/bench -k "workspace_cannot or missing_sdk"
aliases:
- 对照实验中止
- bench abort
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户 2026-10-20 深度审查后要求修复。
必须保持：单次运行出错（起始提交写错、工作区建不出、Agent 异常）记 status=error 并继续后续用例；
只有缺 Cursor SDK、没设 CURSOR_API_KEY（BenchUnavailable）时整个实验中止。
入口：pmem bench / run_bench。
