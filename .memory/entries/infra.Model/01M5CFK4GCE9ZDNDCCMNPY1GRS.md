---
id: 01M5CFK4GCE9ZDNDCCMNPY1GRS
module: infra.Model
entity: Constants
kind: decision
status: active
supersedes:
- 01M59J8Y2TQ3GZTSZSAYZNTGRT
anchors:
- src/pmem/core/entry.py#KIND_LABELS
- src/pmem/core/entry.py#VISIBLE_STATUSES
- src/pmem/core/entry.py#REPLACING_STATUSES
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: KIND_LABELS、VISIBLE_STATUSES 集中在 core/entry.py；替代关系只由 Entry.replaces 计算
aliases:
- 常量重复
- 类型中文名
- 可见状态
- 扩展 kind
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
决定：跨模块共用的记忆常量集中在 core/entry.py：KIND_LABELS（类型中文名）、VISIBLE_STATUSES（检索可见状态）被检索、图谱、Wiki、健康报告、CLI、闸门直接导入。
原因：原先各自复制一份，新增 kind 或状态时只改一处会出现“检索看得见、Wiki 不显示”。
扩展 kind/status 时只改这里，再跑全量测试。
更正：REPLACING_STATUSES 不再被其他模块导入，只在 Entry.replaces 里用，替代关系统一由 replaces() 计算；
旧记忆列的“尚未收归的重复常量”已收归：MIN_SEARCHES_FOR_IDLE 只在 metrics/events.py 定义，git log 解析在各版本库适配器里。
