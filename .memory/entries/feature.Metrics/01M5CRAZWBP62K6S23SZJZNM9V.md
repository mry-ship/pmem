---
id: 01M5CRAZWBP62K6S23SZJZNM9V
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes:
- 01M5CGMVGQHC1CCJD0MFR9MK0Y
anchors:
- src/pmem/cli/main.py#_bench
- src/pmem/bench/runner.py#run_bench
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: bench 单个用例失败不中止；--dry-run 有用例没跑起来也算失败
verify: uv run pytest tests/bench
aliases:
- 对照实验
- bench dry-run
- 用例有效
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 深度审查和复查后要求修复。
必须保持：
1) 单次运行出错（起始提交写错、工作区建不出、Agent 异常）记 status=error 并继续后续用例；
   只有缺 Cursor SDK、没设 CURSOR_API_KEY（BenchUnavailable）时整个实验中止，命令行打一行原因返回 2。
2) pmem bench --dry-run：只要有用例 status 不是 dry_run（没跑起来）、或在起始提交上验收已通过、或一个用例都没跑，就返回 1 并分别列出。
   原先起始提交写错的用例 passed=False，被当成“用例有效”。
3) --arms 只能取 on、off；用例文件不存在或格式错误时返回 2，不给异常栈。
入口：pmem bench（cli/main.py 的 _bench）/ run_bench。
