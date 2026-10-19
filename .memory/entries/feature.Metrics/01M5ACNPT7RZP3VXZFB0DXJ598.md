---
id: 01M5ACNPT7RZP3VXZFB0DXJ598
module: feature.Metrics
entity: Quality
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_pitfall_share
- src/pmem/metrics/report.py#_repeats
- src/pmem/metrics/health.py#_repeat_corrections
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: report 加防错类占比和对话内重复率，health 加同一议题反复更正；基线 14%、50%
aliases:
- 防错类占比
- 重复率
- 反复更正
- 验收
---
决定（v0.3 验收度量）：pmem report 的【收益】增加两行，pmem health 增加一节。
- 防错类占比：本期新写记忆里排除项、风险、更正的占比，和之前已有记忆对比；低于 30% 提示“记忆可能在变成改了什么的记录”。
- 对话内重复：带对话 id 的检索里，同一对话给过全文又整条再给的条数和比例，以及已折叠成标题的条数。
- health【同一议题反复更正】：统计期内同一模块同一议题有 2 条及以上更正，作为“同类错误重复出现”的信号，提示补排除项或风险、按 pmem-compact 合并。
上线时本仓库基线（30 天）：防错类占比 14%，对话内重复 50%（465/921），已折叠 0（MCP 服务未重启）。验收目标：防错类 ≥30%，对话内重复 <5%。
