---
id: 01M7WTAJTTTQ4P3J0Q6DFGVEZB
module: infra.Model
entity: EnforcedBy
kind: feature
status: active
supersedes:
- 01M7WFSBJ6TCW4ECMN20M18CGK
anchors:
- src/pmem/core/entry.py#enforced_mark
- src/pmem/core/entry.py#Entry
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: enforced_by 字段与 enforced_mark 双态标题标注
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 实现或改 v0.7 规则化字段或标题标注时
---
需求来源：v0.7 规则化；深检要求标题标注区分「规则仍有效」与「规则需核实」。

必须保持：
- 记忆可选字段 enforced_by: [路径#规则名]，写法同 anchors；to_markdown/from_markdown 读写；Entry.enforced 表示非空；空列表不写进 YAML 头；旧版经 extra 保留。
- enforced_mark(enforced_by, problems)：无 enforced_by 不标；problems 中有「规则」开头（规则文件缺失/改过/找不到符号）时标「（规则需核实）」；否则标「（已由规则拦截）」。
- config 含 health.rule_min / health.rule_searches 默认值。

入口：core/entry.py#enforced_mark、core/entry.py Entry、core/config.py。
