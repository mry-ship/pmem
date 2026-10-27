---
id: 01M5Y1SRC18WCERGWZXSCTKMC1
module: infra.Common
entity: Roadmap
kind: plan
status: active
supersedes:
- 01M5KTHTCJM3DFWDDS8FX3FHQR
anchors:
- docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md
- src/pmem/core/schema.py
revision: git:5fd9632
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: v0.7 进行中：下一刀规则化与 enforced_by，再边界校验与 when
applies: 做类型安全与规则化时，版本号按 v0.7，不占 v0.6。
---
需求来源：用户 2026-10-27 要求再开 v0.7。
范围不变，见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md 与 Issue #15。
已开工：core/schema.py 基础 expect_*。
仍要做（按设计第5节）：
  1) 健康报告可写成规则的教训与 enforced_by；
  2) 边界校验接入 config/modules/entry/Hook；
  3) facets/when；
  4) MCP 返回契约与 pyright。
v0.6 已是模块规格，不要把类型安全排回 v0.6。
