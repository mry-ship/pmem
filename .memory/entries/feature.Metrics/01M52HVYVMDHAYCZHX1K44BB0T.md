---
id: 01M52HVYVMDHAYCZHX1K44BB0T
module: feature.Metrics
entity: HealthIdle
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#build_health
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 健康报告
- 没人检索
- 废弃模块
verified: '2026-10-19'
---
决定：健康报告里“统计期内本机没检索过的模块”不再列出已废弃的模块（modules.yaml 里 status: deprecated）。
原因：废弃模块本来就不再开发，没人检索是正常的，列出来会让负责人误以为路径没登记全或闸门失效。
风险：废弃模块的路径如果其实还有人在改，这一段不会提示，只能从 doctor 覆盖率或闸门日志看出来。
