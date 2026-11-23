---
id: 01M83HKVAPJN5VMR4V73F1QDEA
module: feature.Spec
entity: ClosedSetCheck
kind: feature
status: active
supersedes:
- 01M7X861E28X88C68MQPS9V6F8
- 01M83GYRGGHAF2XHCJ5A339VD2
- 01M83GZHXSATBAN0CM42R0EYN7
anchors:
- src/pmem/generate/spec_closed.py#_sentences
- src/pmem/generate/spec_closed.py#_one_field
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: spec closed：纯占位符与无签名不报一致
verify: uv run pytest tests/test_spec_closed.py -q
source:
  kind: code
---
需求来源：审查发现 closed 原文纯占位符与无签名字段名会误报一致；按确认边界收紧判定。

必须保持：
- 命令仍是 pmem spec closed，可选 --module。只读，不写规格文件。
- 自动输出只有一致、可能不一致、无法判断，不出现已确认不一致。
- --check 仍只看程序和现状里的空标记。
- 入参出参必须一行一个字段名。散文或「含某某」是无法判断。
- 原文整句若去掉占位符后没有任何字面量，报无法判断（只有占位符，无法按字面核对）。
- 有字面量时按顺序在代码里找这些字面量；找不到报可能不一致。
- 字段无类型签名时，即使代码里出现同名也报无法判断，不报一致；找不到名字仍报可能不一致。有签名时仍走参数注解核对。
- 没有程序设计也没有模块现状时，只输出一行「无法判断 规格 没有程序设计或模块现状」。
- 路径不在、路径在但符号不在，是可能不一致。路径逃出项目是无法判断。
- 必须保持的行为始终无法判断。不读策划，不把 design-gap 报成不一致。

入口：pmem spec closed；src/pmem/generate/spec_closed.py。
