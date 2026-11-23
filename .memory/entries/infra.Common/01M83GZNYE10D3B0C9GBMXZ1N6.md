---
id: 01M83GZNYE10D3B0C9GBMXZ1N6
module: infra.Common
entity: Docs
kind: risk
status: archived
supersedes: []
anchors:
- docs/architecture.md
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 0.7.3 架构与设计路线表未对齐发版
verify: architecture 与设计稿 §14 是否出现 0.7.2/0.7.3 与工程质量技能
applies: 发版后核对用户文档与设计路线时
archived:
  'on': '2026-11-23'
  from: active
  by: 1002378395@qq.com
source:
  kind: document
---
风险：README 与手册已到 0.7.3，但 architecture 几乎无 0.7.3 能力；
设计稿路线表停在 0.7.0，且 §14 表仍写规格提醒默认不提示、与 §14.6/现行默认开启矛盾。
手册效果表少写「记忆闸门优先于规格闸门」。
Wiki 在另仓，本仓无法核对。
