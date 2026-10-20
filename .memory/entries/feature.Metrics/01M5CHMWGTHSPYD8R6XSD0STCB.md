---
id: 01M5CHMWGTHSPYD8R6XSD0STCB
module: feature.Metrics
entity: Bench
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py#run_bench
- src/pmem/bench/runner.py#sdk_executor
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 单个用例工作区建不出来曾让整个 bench 中止，因为 git 失败也抛 RuntimeError
verify: uv run pytest tests/bench/test_bench.py -k "cannot_be_built or missing_sdk"
aliases:
- 评测中止
- bench abort
- 实验中断
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
现象：一个用例的起始提交写错（工作区建不出来），整个 pmem bench 直接中止，其他用例都没跑。
根因：run_bench 用 except RuntimeError: raise 来中止“缺 SDK / 没设 API Key”这类全局问题，但 bench 里调用 git 失败时同样抛 RuntimeError，于是单个用例的错误也被当成全局问题。
现在全局问题改抛专用的 BenchUnavailable，其他异常一律记为该次运行失败、继续后面的用例。
另：hooks 的 watchdog 测试 test_code_update_reloads_idle_child 偶发 WinError 6，重跑通过，疑似子进程未设置 stderr，尚未处理。
