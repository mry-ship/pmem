---
id: 01M640JGCXTRZYDQMG3XV50JG7
module: feature.Onboarding
entity: CompactKind
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: compact 技能合并后保持 exclusion/risk/correction，不要收成 conclusion
verify: uv run pytest tests/test_feature_records.py -k compact_skill
applies: pmem init 生成的 pmem-compact 技能
---
用户要求：按 pmem-compact 合并时保留防错类型，不要一律收成 conclusion。

必须保持：技能写明排除过的方向用 exclusion，风险用 risk，推翻旧结论用 correction；
旧记忆已是这三类的，合并后保持，不要收成 conclusion。
其余用 conclusion 或 decision。
pmem init 会覆盖各 Agent 技能目录里的副本。

适用：pmem init 生成的 pmem-compact 技能。

入口：src/pmem/generate/templates.py 的 COMPACT_SKILL
