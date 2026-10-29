---
id: 01M63YZWK9P6GQWNNWQKPSEQPG
module: feature.Metrics
entity: FixOrder
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/cite.py
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/index/store.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 先改检索降权与催写去重；采用天花板约25-35%，催写约80%
aliases:
- 提高空间
- 优化优先级
---
决定：先改检索精度和催写状态，不先改采用阈值、不把 analysis_reminder 默认扳回 true。

当前两边共同缺口与提高空间（2026-10-29）：
1) 采用 TM 10% / 本仓库 17%：闸门只逼查。
   TM 55% 分数<0.05 是检索噪声。
   去掉这些零重合分母可到约 22%；
   再把反复未采用的降权、排查结果里的 exclusion 必须回应，字面采用天花板大约 25–35%（阈值 0.15 加换说法，到不了 50%）。
2) 防错 TM 15 天 21%、10-19 后 32%：写入侧已达标，30 天 8% 等导入出窗。
   剩下是 compact 默认 conclusion、exclusion 条数少（本仓库 11/331）。
   compact 保留防错 kind + 正文含「不要」时提示 kind，15 天可稳在 30% 以上；
   exclusion 占比另算。
3) 催写 TM 59% / 本仓库 66%：14 次未转化里 8 次是长对话再催已写模块。
   按 source_conversation 认已写、不重复催，可到约 75–80%。
   用户不续跑 followup 和「无新结论」是产品上限，到不了 90%。
4) 报告：采用/习惯 15=30=90 是因为事件日志只有约 13 天；防错占比应同时给本机作者切片。

不做：为抬采用率把字面阈值降到 0.05（会把近失算成用上）；为催写把 analysis_reminder 产品默认改回 true。
