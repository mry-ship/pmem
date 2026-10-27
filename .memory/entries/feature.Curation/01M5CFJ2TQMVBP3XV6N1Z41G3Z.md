---
id: 01M5CFJ2TQMVBP3XV6N1Z41G3Z
module: feature.Curation
entity: CorpusQuality
kind: risk
status: active
supersedes:
- 01M5AB7K4WGM5SKTM03C00NK2W
anchors:
- src/pmem/metrics/report.py#_pitfall_share
- src/pmem/core/quality.py#content_hints
- src/pmem/hooks/reminders.py#on_stop
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 记忆库易变成变更日志、排除项太少；10-19 发现的几处成因已修，需靠占比持续观察
aliases:
- 记忆质量
- 变更日志化
- 采用率低
- 排除项太少
- 重复返回
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
风险：记忆库容易变成“现在代码怎么做”的变更日志，最能防错的排除项、风险很少。
2026-10-19 全库快照：现行 147 条中决定占 65%、排除项仅 2 条；
96 个议题里 62 个只有 1 条；
pmem report 返回 312 条只被采用 60 条（19%）；
带对话 id 的检索有 40% 是同一对话里已经返回过的。
这些数字是当时的快照。
更正：快照里列出的几个成因已修：
- 正文以“决定：”开头会让变更记录检测失效，现在先去掉类型前缀再判断；
- 服务端已做对话内去重，给过全文的只返回标题；
- 摘要不再出现“决定：决定：”重复前缀，改用 summary 或首句；
- 结束提醒改为按模块写功能记录，教训（含排除项）单独要求。
仍有效：省 token 的大头在“少走弯路、少读代码”，不在压缩记忆文本；不要按采用率调排序（只在本机离线算出，会让不同人的检索结果不一致）。
持续观察：pmem report 的防错类占比（只算教训，目标 ≥30%）和对话内重复率。
