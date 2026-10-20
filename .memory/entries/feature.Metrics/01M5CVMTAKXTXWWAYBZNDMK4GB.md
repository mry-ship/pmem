---
id: 01M5CVMTAKXTXWWAYBZNDMK4GB
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes:
- 01M5CRAZWBP62K6S23SZJZNM9V
anchors:
- src/pmem/cli/main.py#_bench
- src/pmem/bench/runner.py#load_cases
- src/pmem/bench/runner.py#run_bench
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: bench 单个用例失败不中止；--dry-run 有用例没跑起来算失败；用例文件格式先校验
verify: uv run pytest tests/bench tests/test_robustness.py -k bench
aliases:
- 对照实验
- bench dry-run
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 深度审查和两轮复查后要求修复。
必须保持：
1) 单次运行出错记 status=error 并继续；只有缺 Cursor SDK、没设 CURSOR_API_KEY（BenchUnavailable）时整个实验中止，命令行打一行原因返回 2。
2) --dry-run：有用例 status 不是 dry_run、在起始提交上验收已通过、或一个用例都没跑时返回 1 并分别列出。
3) --arms 只能取 on、off；用例文件不存在、顶层不是键值对、cases 不是用例列表时返回 2，不给异常栈。
入口：cli/main.py _bench、bench/runner.py load_cases / run_bench。
