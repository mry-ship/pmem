---
id: 01M7WFSBJ6TCW4ECMN20M18CGK
module: infra.Model
entity: EnforcedBy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#Entry
- src/pmem/core/config.py
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 记忆可写 enforced_by；config 含 health.rule_min/rule_searches
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 实现或改 v0.7 规则化字段时
---
需求来源：架构规划 P2 / v0.7 阶段 1——把可机械检查的经验标成已由规则保障，避免只靠记忆提醒、规则与记忆各说各话。
必须保持：记忆可选字段 enforced_by: [路径#规则名]，写法同 anchors；
to_markdown/from_markdown 读写；
Entry.enforced 表示非空；
空列表不写进 YAML 头。
旧版不认识该字段时仍经 extra 保留。
config 增加 health.rule_min / health.rule_searches 默认值。
适用：实现或改 v0.7 规则化字段、health 规则化阈值时。
入口：core/entry.py、core/config.py。
