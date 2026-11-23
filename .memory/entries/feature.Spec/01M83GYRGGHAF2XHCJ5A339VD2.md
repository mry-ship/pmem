---
id: 01M83GYRGGHAF2XHCJ5A339VD2
module: feature.Spec
entity: ClosedSetCheck
kind: risk
status: archived
supersedes: []
anchors:
- src/pmem/generate/spec_closed.py#_sentences
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: spec closed 原文占位符会误报一致
verify: 用只含 <错误码> 或请先运行 <命令> 对无关代码跑 closed，应不为一致
applies: 规格原文行含 <占位符> 且用 pmem spec closed 核对时
archived:
  'on': '2026-11-23'
  from: active
  by: 1002378395@qq.com
source:
  kind: code
---
风险：_sentences 把 <...> 拆成 .*? 再 DOTALL 搜索。
整句只有占位符时模式变成 .*?，任意代码都报一致；
固定字少、占位符宽时也会把无关后文判成一致。
测试未覆盖假阳性。
建议：纯占位符判无法判断；
占位符两侧字面量须各自命中，或禁止过宽通配。
