---
id: 01M5A8NDQMTBVC9GH7M5MG0F3V
module: feature.Metrics
entity: Robustness
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/events.py
- src/pmem/metrics/report.py
- src/pmem/bench/runner.py#run_bench
- src/pmem/bench/runner.py#run_check
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 日志轮转
- 覆盖率
- 评测
- bench
- 超时
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：
1) 事件日志轮转时改名失败（Windows 上文件被另一进程占用）就跳过本次轮转，照常追加；原先抛异常，事件直接丢失。
2) report 的“有记忆的模块数”只数登记模块，与分母（登记模块总数）同口径；原先把已删除或未登记模块也算进去，覆盖率可能超过 100%。
3) bench：验收命令超时（600 秒）记为失败而不是崩溃；
   SDK 执行器用定时器到时取消运行；
   单次运行出普通异常记 status=error、其余继续，只有 RuntimeError（环境问题）整体中止；
   summary.md 放在 finally 里写，中途中止也留下汇总。
风险：SDK 取消依赖 run.cancel 生效，如果 SDK 不响应取消，仍会卡住。
