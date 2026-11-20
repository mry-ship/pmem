---
id: 01M7WFT5WD5P5HZ9YTWRP45J8H
module: feature.Gate
entity: EnforcedBy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/memories.py#_lines
- src/pmem/hooks/guard.py#_pitfalls
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 摘要与拦截标「已由规则拦截」并把已保障教训靠后排
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 改 Hook 摘要行或拦截坑列表时
---
需求来源：v0.7——摘要与拦截要让 AI 看出哪些坑已被规则兜住。
必须保持：读码摘要与拦截列表的标题行，对 enforced_by 非空的记忆标「（已由规则拦截）」；
拦截 pitfalls 与上级 pitfalls 排序时已保障的靠后。
适用：改 Hook 摘要行或拦截坑列表时。
入口：hooks/memories.py#_lines、hooks/guard.py#_pitfalls。
