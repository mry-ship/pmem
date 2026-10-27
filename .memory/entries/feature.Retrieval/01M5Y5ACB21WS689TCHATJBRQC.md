---
id: 01M5Y5ACB21WS689TCHATJBRQC
module: feature.Retrieval
entity: Ranking
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 检索加分含 risk；与 exclusion/correction 同属防错类轻加成
verify: uv run pytest tests/index -q
applies: 改检索加分种类时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：防错类占比与采用率偏低，排序上让风险与排除项、更正一样略优先露出。
必须保持：_score 对 exclusion、correction、risk 加 0.05；不加相关度阈值过滤（见同议题 exclusion）。
入口：src/pmem/index/store.py BOOSTED_KINDS。
