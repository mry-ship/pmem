---
id: 01M7WFXX82TK5PVVZ5PHYZ4TQ0
module: infra.Model
entity: EnforcedBy
kind: exclusion
status: active
supersedes: []
anchors:
- docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 排除：阶段1功能记录不要 supersede 整份 v0.7 规划
verify: pmem search --module infra.Common --brief 规划 Roadmap
applies: 写 v0.7 分阶段落地的功能记录时
---
排除：把只实现了 v0.7 阶段 1（enforced_by / 规则候选）的功能记录，用 supersedes 直接替代整份「v0.7 进行中」规划。
原因：when/facets、边界校验等还没做，规划仍指导后续阶段；
替代后检索看不到未完成项。
现行：阶段功能记录不 supersede 总规划；
总规划等 0.7.0 收齐再由功能记录或 correction 收口。
