---
id: 01M7WFT57NBDJCE0K56WPC0XHA
module: feature.Metrics
entity: RuleCandidates
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#_rule_candidates
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: health 列出可写成规则的教训；已有 enforced_by 的议题跳过
verify: uv run pytest tests/metrics/test_health.py -k rule_candidates
applies: 改 health 规则化候选阈值或文案时
---
需求来源：v0.7 健康报告「可以写成规则的教训」。
必须保持：同模块同议题现行防错类（exclusion/risk/correction）≥ health.rule_min（默认 3），或已在反复更正里且该议题检索次数 ≥ health.rule_searches（默认 5）时列入；
议题上已有任一 enforced_by 记忆则跳过；
给出建议规则形态与近例标题。
入口：metrics/health.py#_rule_candidates、render。
