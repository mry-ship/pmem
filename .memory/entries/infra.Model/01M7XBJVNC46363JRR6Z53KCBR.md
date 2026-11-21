---
id: 01M7XBJVNC46363JRR6Z53KCBR
module: infra.Model
entity: Provenance
kind: feature
status: active
supersedes:
- 01M7X85VHYA10M038CMP99AA0C
anchors:
- src/pmem/core/entry.py#parse_valid_from
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 生效日只接受 YYYY-MM-DD，来源种类不写成已核对
verify: uv run pytest tests/core/test_entry.py -k valid_from
applies: 读写真记忆的 valid_from，或放宽日期解析时
aliases:
- 生效日
- valid_from
- source.kind
source:
  kind: code
---
需求来源：发 0.7.2 时核对生效日。
Python 3.11 起 date.fromisoformat 会收下 20260101、2026-W01-5，存成原字符串后和 as_of 按字符串比较会对不上。
用户要求生效日必须是 YYYY-MM-DD。

必须保持：
- source.kind 可选，只能是 human、code、test、conversation、document、inference。缺省未知。不写入 verified，不参与排序。
- 写入、核对、归档、覆盖草稿都不丢。没传或空串沿用旧值，不能清空。
- valid_from 可选。只接受日历日 YYYY-MM-DD：整段匹配这个格式，并且 date.fromisoformat 成功。紧凑日期、周日期、不存在的月日都拒绝。缺省时生效日等于 note_date。
- 不把紧凑日期或周日期改写成标准日再存。
- 旧记忆没有这两个字段也能读，不必迁移。

入口：src/pmem/core/entry.py 的 parse_valid_from、source_kind、effective_date。
