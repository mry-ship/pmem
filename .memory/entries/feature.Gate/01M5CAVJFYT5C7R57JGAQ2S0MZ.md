---
id: 01M5CAVJFYT5C7R57JGAQ2S0MZ
module: feature.Gate
entity: FeatureReminder
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_written
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 只写了教训也算写过，不再提醒补功能记录，靠覆盖率发现
aliases:
- 漏写
- 覆盖率
---
风险：结束提醒判断“写过记忆”时不区分类型，只写了一条教训的模块也算写过，不会再提醒补功能记录。
原因：会话状态 written 只记模块和议题，终端 pmem record 的登记也拿不到类型；要区分得在 after-mcp 解析返回的 kind、终端解析 --kind，两条路径都改。
影响：功能记录可能漏写，pmem report 的“功能记录覆盖”会偏低，这是发现漏写的主要手段。若覆盖率长期低于 80%，再按类型区分 written。
