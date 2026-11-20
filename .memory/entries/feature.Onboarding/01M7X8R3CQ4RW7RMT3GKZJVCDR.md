---
id: 01M7X8R3CQ4RW7RMT3GKZJVCDR
module: feature.Onboarding
entity: AsOf
kind: feature
status: active
supersedes: []
anchors: []
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: doctor 现行条数等替代生效
---
需求来源：doctor 的现行记忆条数要和检索用同一套替代生效口径。

必须保持：
- 统计现行记忆时，写了未来 valid_from 的后继先不把被替代的那条藏起来。
- 没写 valid_from 的替代仍然立即生效。

入口：src/pmem/cli/doctor_cmd.py 里统计现行记忆的那一段。
