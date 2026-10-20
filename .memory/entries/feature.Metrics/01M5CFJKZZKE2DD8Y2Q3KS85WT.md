---
id: 01M5CFJKZZKE2DD8Y2Q3KS85WT
module: feature.Metrics
entity: Quality
kind: decision
status: active
supersedes:
- 01M5ACNPT7RZP3VXZFB0DXJ598
anchors:
- src/pmem/metrics/report.py#_pitfall_share
- src/pmem/metrics/report.py#_repeats
- src/pmem/metrics/health.py#_repeat_corrections
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: report 加防错类占比（只算教训）和对话内重复率，health 加同一议题反复更正
aliases:
- 防错类占比
- 重复率
- 反复更正
- 验收
---
决定（v0.3 验收度量）：pmem report 的【收益】增加两行，pmem health 增加一节。
- 防错类占比：本期新增教训里排除项、风险、更正的占比，和之前对比；低于 30% 提示“记忆可能在变成改了什么的记录”。更正：分母只算教训类，功能记录和规划不计（报告文案为“占本期新增教训”）。
- 对话内重复：带对话 id 的检索里，同一对话给过全文又整条再给的条数和比例，以及已折叠成标题的条数。
- health【同一议题反复更正】：统计期内同模块同议题有 2 条及以上更正，提示补排除项或风险、按 pmem-compact 合并。
上线时本仓库基线（30 天，当时分母含全部记忆）：防错类 14%，对话内重复 50%（465/921）。验收目标：防错类 ≥30%，对话内重复 <5%。
