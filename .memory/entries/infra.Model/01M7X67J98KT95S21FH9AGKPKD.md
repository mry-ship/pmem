---
id: 01M7X67J98KT95S21FH9AGKPKD
module: infra.Model
entity: ValidFrom
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#to_markdown
- src/pmem/index/store.py#superseded
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: kind 与 valid_from 做成字段，as_of 用生效日
verify: 旧记忆不写 valid_from 时 as_of 结果与现在相同；只写在 source 字典里的 kind 经 confirm 后仍在
applies: 增加 source.kind 或 valid_from，或让历史查询使用生效日时
aliases:
- 生效日
- 来源种类
---
决定：source.kind 与 valid_from 做成条目字段，as_of 用生效日而不是写下日。

原因：今天才能补记的往年方案，note_date 是今天。
as_of 现在只比较 note_date（index/store.py 的 superseded、_visible_items），历史查询永远看不到这条。
source 写回时只留 conversation（entry.py 的 to_markdown），kind 塞进这个字典会在核对、归档、覆盖草稿时丢失。

排除：把 kind 只放进现有 source 字典；把 valid_from 只留在未知字段里（文件能往返，查询用不到）；现行检索也按 valid_from 隐藏。现行检索仍表示现在。

代价：生效日晚于今天的记忆，现在的检索仍会返回，只在字段里看得到 valid_from。缺省等于 note_date，旧记忆的 as_of 结果不变。替代是否生效，用后继那条的 valid_from。

来源缺省和未核对只出现在检索字段里。摘要「需核实」仍只表示锚点过期。seed 是状态，不是核对。
