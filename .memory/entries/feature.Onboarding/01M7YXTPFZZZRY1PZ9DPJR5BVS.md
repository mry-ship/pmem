---
id: 01M7YXTPFZZZRY1PZ9DPJR5BVS
module: feature.Onboarding
entity: MinimalChange
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py
- src/pmem/bench/runner.py
- src/pmem/metrics/audit.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 最小充分实现不进记忆核心
scope: project
verify: git diff 不改 src/pmem/core/entry.py 的 KINDS、src/pmem/hooks、src/pmem/index、src/pmem/bench/runner.py
  的 ARMS
applies: 给 pmem 加工程决策或最小实现能力时
aliases:
- 最小充分实现
- Minimal Complete Change
- 最小方案
---
不要为 Minimal Complete Change 新增记忆类型、Hook、命令、MCP 工具，也不要改检索排序、召回闸门或 bench 的 on/off。
原因：v0.7.2 的 KINDS 是闭集，未知 YAML 头只会原样保留，record_memory 不会写入新字段；
bench 的 on 组只注入现有记忆规则和 MCP，off 组两者都没有；
metrics/audit.py 已是 health 里的召回审计。
决策流程放进独立 alwaysApply 规则和按需技能即可，避免为了少写代码去动记忆核心。
若技能漏触发，只在那条独立规则里补一句触发条件，仍不改 Hook。不要把原则写进记忆规则正文，否则下一次 bench 的 on 组会把工程决策和记忆价值混在一起。
