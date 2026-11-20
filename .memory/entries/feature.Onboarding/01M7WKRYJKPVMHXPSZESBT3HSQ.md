---
id: 01M7WKRYJKPVMHXPSZESBT3HSQ
module: feature.Onboarding
entity: Templates
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: init 技能：when 指引与 consolidate 规则升级步骤
verify: uv run pytest tests/test_v07_evidence.py -k consolidate_skill
applies: 改 bootstrap/compact/consolidate 技能或适用条件、规则化指引时
---
需求来源：v0.7 §3.1；设计要求 pmem-consolidate 增加把「可以写成规则的教训」升级成规则的一步。

必须保持：
1) pmem-consolidate 技能在 health 收口流程中含「可以写成规则的教训」步骤：与用户确认后写规则，再写功能记录，enforced_by 填规则文件#规则名，supersedes 填被替代教训。
2) pmem-compact 指引：适用条件不同时能枚举的写 when（需 facets），其余写 applies。
3) bootstrap 指引：平台/渠道/版本能枚举的写 when，其余写 applies（见同模块 Templates 相关功能记录）。
4) 重跑 pmem init 后技能文件带上上述口径。

入口：src/pmem/generate/templates.py（CONSOLIDATE_SKILL、COMPACT_SKILL）；pmem init。
