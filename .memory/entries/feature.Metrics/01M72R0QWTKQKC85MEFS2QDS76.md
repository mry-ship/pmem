---
id: 01M72R0QWTKQKC85MEFS2QDS76
module: feature.Metrics
entity: HarnessReport
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_harness
revision: git:dbfdab4
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: report 增加 harness 三项：漏改采纳、验证回合、3 天返工率
verify: uv run pytest tests/hooks/test_harness.py -k harness_report
---
需求：实验能量化。必须保持的行为：
- pmem report 在有相关事件时输出【harness 实验】：漏改提示伙伴文件随后被改的比例、配置了验证命令的回合跑过验证的比例、统计期内改过的文件 3 天内又被改的比例；另附无记忆轻提示后带 path 查了的比例。
- 事件：context、context_nudge、harness_nudge（partners）、harness_verify（ran）。
入口：metrics/report.py 的 _harness / _render_harness。
