---
id: 01M7WTAX6WWG8S1J6N4H8HH70F
module: feature.Gate
entity: EnforcedBy
kind: feature
status: active
supersedes:
- 01M7WFT5WD5P5HZ9YTWRP45J8H
anchors:
- src/pmem/hooks/memories.py#_lines
- src/pmem/hooks/memories.py#fill_stale
- src/pmem/hooks/guard.py#_pitfalls
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 摘要双态标规则拦截/需核实；延迟核对时占位替换
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 改 Hook 摘要行、fill_stale 或拦截坑列表时
---
需求来源：v0.7 摘要要区分规则仍有效与规则需核实；延迟 stale 核对时也要一致。

必须保持：
- 读码摘要与拦截列表对 enforced_by 非空的记忆用 enforced_mark：规则问题标「规则需核实」，否则标「已由规则拦截」。
- defer_stale 时 enforced 先写占位符，fill_stale 用核对结果替换，与 stale 占位同一时机。
- 拦截 pitfalls / 上级 pitfalls 排序时已保障（规则仍有效）的靠后。

入口：hooks/memories.py#_lines、fill_stale；hooks/guard.py#_pitfalls。
