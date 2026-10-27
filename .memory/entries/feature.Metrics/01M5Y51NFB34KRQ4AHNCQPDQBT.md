---
id: 01M5Y51NFB34KRQ4AHNCQPDQBT
module: feature.Metrics
entity: Health
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#_hot_returns
- src/pmem/metrics/health.py#render
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: health 列出返回≥3次的记忆供收口；冷模块建议指向 consolidate
verify: uv run pytest tests/metrics/test_health.py -k hot_returns
applies: 负责人跑 pmem health 收口时
aliases:
- 冷记忆
- 返回未用
- hot_returns
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：P1 冷记忆/返回未用/重复模块收口需要健康报告给可执行清单。
必须保持：
1) 本机检索足够（≥MIN_SEARCHES_FOR_IDLE）时，health 增加「返回 ≥3 次的记忆」节（同一对话只算一次），附 confirm/correction/archive/改 summary/migrate 与指向 pmem report 的「返回未采用」。
2) 「统计期内没检索过的模块」动作文案补充可按 pmem-consolidate 收口。
3) 疑似重复模块等原有节不变。
入口：src/pmem/metrics/health.py（_hot_returns、render）。
