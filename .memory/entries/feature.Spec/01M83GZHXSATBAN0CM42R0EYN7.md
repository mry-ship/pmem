---
id: 01M83GZHXSATBAN0CM42R0EYN7
module: feature.Spec
entity: ClosedSetCheck
kind: risk
status: archived
supersedes: []
anchors:
- src/pmem/generate/spec_closed.py#_one_field
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 无签名字段名只要词边界命中就报一致
verify: 入参只有 name、代码字符串含 name 时不应报一致
applies: 规格入参/出参无类型签名、走 pmem spec closed 时
archived:
  'on': '2026-11-23'
  from: active
  by: 1002378395@qq.com
source:
  kind: code
---
风险：无签名分支用词边界全文搜索，字符串字面量、注释里的同名也会报一致。有签名时走 AST 较稳。建议：无签名最多报无法判断，或要求出现在参数/字段定义位置。
