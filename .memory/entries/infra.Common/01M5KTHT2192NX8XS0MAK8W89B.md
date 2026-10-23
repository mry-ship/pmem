---
id: 01M5KTHT2192NX8XS0MAK8W89B
module: infra.Common
entity: Roadmap
kind: decision
status: active
supersedes: []
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 模块规格定为 v0.6；类型安全顺延为 v0.7，范围不变
applies: 排版本、改 README 路线表或总设计第 14 节时。
aliases:
- 模块规格
- 类型安全
- v0.6
- v0.7
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
决定（2026-10-23，用户指定）：模块规格定为 v0.6（Issue #16）。类型安全顺延为 v0.7（Issue #15），范围不改。
原因：用户要先有可带走、可重做的模块现状文档。类型安全设计稿仍是计划、未开工，把已经写过的版本号让出来，避免两条都叫 v0.6。
没选：两条一起叫 v0.6，或让模块规格排到 v0.7、类型安全继续占 v0.6。
代价：README、总设计第 14 节和类型安全设计稿文首都要改版本号。安装包仍是 0.5.1，发布 v0.6 时再对齐。
