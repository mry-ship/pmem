---
id: 01M5KTHTCJM3DFWDDS8FX3FHQR
module: infra.Common
entity: Roadmap
kind: plan
status: active
supersedes:
- 01M5FG7SKTTNK3QTTAKMNW2K56
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: v0.7 类型安全与规则化，范围不变，从 v0.6 顺延
applies: 做类型安全与规则化时，版本号按 v0.7，不占 v0.6。
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
需求来源：用户（2026-10-21）定的类型安全与规则化，2026-10-23 顺延为 v0.7。
范围不变，见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md 与 Issue #15。
仍要做：教训升级成规则并写 enforced_by、facets/when、边界校验、MCP 返回契约与 pyright。
v0.6 已改为模块规格（Issue #16），不要再把类型安全排回 v0.6。
