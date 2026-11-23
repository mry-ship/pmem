---
id: 01M83PNX7F7HH71PNW6YR8M9FA
module: feature.Spec
entity: ClosedSetCheck
kind: feature
status: active
supersedes:
- 01M83HKVAPJN5VMR4V73F1QDEA
anchors:
- src/pmem/generate/spec_closed.py#_sentences
- src/pmem/generate/spec_closed.py#_ordered
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 原文核对剥掉一行说明前缀，只在同一文件里按间距找字面量
verify: uv run pytest tests/test_spec_closed.py -q
applies: 运行 pmem spec closed 核对原文整句时
aliases:
- 说明前缀
- 跨文件命中
source:
  conversation: b0769dda-9730-42f8-84a2-6bf9080d94b7
  kind: code
---
需求来源：原文行带「规格闸门拦截全文：」这样的说明前缀会误报可能不一致；单字和跨文件按顺序出现会误报一致。
必须保持：命令仍是 pmem spec closed，只读。
输出只有一致、可能不一致、无法判断。
纯占位符仍是无法判断。
一行开头不超过 32 字、且不含占位符的说明前缀先剥掉，再按剩下的字面量核对；
报告仍显示原文整行。
去掉空白后短于 2 字的碎片不当锚点，剩下没有则无法判断。
字面量必须在同一份文件里按顺序出现，相邻两段之间不超过 4000 字。
找不到仍是可能不一致。
无签名字段不报一致、没有规格只报一行、必须保持仍无法判断，都不变。
入口：pmem spec closed；src/pmem/generate/spec_closed.py。
