---
id: 01M640K37WDMDB2JXN4Z73SDXP
module: feature.Curation
entity: Merge
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 不要把 compact 默认 kind 一律改成 exclusion
applies: 按 pmem-compact 合并或改 compact 默认 kind 时
aliases:
- compact默认
- 防错占比
---
排除：不要为了抬防错占比，把 compact 默认 kind 一律改成 exclusion。
没有排除方向的合并产物仍应是 conclusion 或 decision；只有旧记忆已是 exclusion / risk / correction，或正文在讲「不要做某事」时才用防错类。
一律改成 exclusion 会把方案说明伪装成排除项，检索加分和健康报告的防错占比都会虚高。
证据：FixOrder 写的是「保留防错 kind + 正文含不要时提示」，不是「合并默认 exclusion」。
