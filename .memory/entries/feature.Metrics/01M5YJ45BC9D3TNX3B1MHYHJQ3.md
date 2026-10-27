---
id: 01M5YJ45BC9D3TNX3B1MHYHJQ3
module: feature.Metrics
entity: Health
kind: feature
status: active
supersedes:
- 01M5Y51NFB34KRQ4AHNCQPDQBT
anchors:
- src/pmem/metrics/health.py#_hot_returns
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: health 列出返回却未写入≥3次的记忆供收口；冷模块指向 consolidate
verify: uv run pytest tests/metrics/test_health.py -k hot_returns
applies: 负责人跑 pmem health 收口时
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
需求来源：P1 冷记忆/返回未用收口；2026-10-27 核对发现节标题写成「返回≥3次」，实现却是 returned-recorded（返回了没写入）加对不上对话的 CLI 检索。
必须保持：
1) 本机检索足够时，health 增加「返回却未写入 ≥3 次的记忆」节（同一对话只算一次），附 confirm/correction/archive/改 summary/migrate，并指向 pmem report 的「返回未采用」。
2) 「统计期内没检索过的模块」动作文案可按 pmem-consolidate 收口。
3) 疑似重复模块等原有节不变。
入口：src/pmem/metrics/health.py（_hot_returns、render）。
