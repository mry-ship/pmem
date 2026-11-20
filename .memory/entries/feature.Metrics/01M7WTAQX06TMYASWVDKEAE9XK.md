---
id: 01M7WTAQX06TMYASWVDKEAE9XK
module: feature.Metrics
entity: RuleCandidates
kind: feature
status: active
supersedes:
- 01M7WFT57NBDJCE0K56WPC0XHA
anchors:
- src/pmem/metrics/health.py#render
- src/pmem/metrics/health.py#_rule_candidates
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: health 规则候选与双态标注处理说明
verify: uv run pytest tests/metrics/test_health.py -k rule_candidates
applies: 改 health 规则化候选阈值或文案时
---
需求来源：v0.7 health「可以写成规则的教训」；深检对齐双态标注文案。

必须保持：
- 同模块同议题现行防错类（exclusion/risk/correction）≥ health.rule_min（默认 3），或已在反复更正里且该议题检索次数 ≥ health.rule_searches（默认 5）时列入；
  议题上已有任一 enforced_by 记忆则跳过；
  给出建议规则形态与近例标题。
- 处理办法文案须说明：写成规则并写 feature（enforced_by + supersedes 教训）后，规则文件与符号仍在时摘要标「已由规则拦截」并靠后排，否则标「规则需核实」。

入口：metrics/health.py#_rule_candidates、render。
