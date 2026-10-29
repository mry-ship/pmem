---
id: 01M63Y1JRGAKM7RN06D5XJQ5CQ
module: feature.Metrics
entity: PitfallShare
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_pitfall_share
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: TileMatch 15天防错21%才是本机质量；30天8%含导入；采用10%已是修正后
verify: uv run pmem report --days 15 --root <TileMatch>；events.jsonl 首条约 10-16
aliases:
- 15天
- 21%
---
TileMatch 15 天窗（今天往前到 10-14）防错 21%（之前 2%）才是本机当前写入质量；30 天 8% / 90 天 6% 是导入 conclusion 还在窗内。

证据：本机教训 219 条、防错 47 条 = 21.5%，对上 15 天报告。再切：
- 10-16 单日 102 条（compact/沉淀，conclusion 88）防错 8.8%；
- 10-19 起（功能/教训分层、防错催写上线）117 条防错 32.5%，摸到 30% 目标。
15 天的 21% 是这两段的混合物，不是「一直 21%」。

检索/采用/习惯 15=30=90，不是这些指标也变好了：本机 events.jsonl 只从 10-16 开始（约 13 天），短于 15 天窗，所以采用 10%、催写 59% 就是修正之后的数字，仍然差。
期前从未被检索 15 天 264 条 > 30 天 117 条，是更短窗口把更多旧记忆划进「期前」，不是 FarmSudoku 突然冷掉。
