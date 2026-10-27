---
id: 01M5CAVBTDR5YZHM5N3HYM6SY8
module: infra.Model
entity: PlanKind
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#Entry
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 未实现的需求用 plan 类型而非 planned 状态，复用替代链
aliases:
- 规划
- planned
- 待实现
- 需求
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
---
决定：“还没实现的需求”做成新类型 plan，而不是新状态 planned。
原因：状态牵涉归档、恢复、as_of 回看、VISIBLE_STATUSES、REPLACING_STATUSES 和 health 的多处判断，加一个状态要改一串流转规则；
类型只影响检索分组和摘要筛选，且 plan 实现后写 feature 用 supersedes 替代，复用现有替代链即可表达“从规划到落地”。
没选：给 feature 加 planned 状态（要改状态流转）、用正文里写“待实现”标记（检索分不出来）。
代价：plan 和 feature 共用“功能记录”一组，按类型区分；以后若要“规划过期提醒”，按 plan 的日期另算。
