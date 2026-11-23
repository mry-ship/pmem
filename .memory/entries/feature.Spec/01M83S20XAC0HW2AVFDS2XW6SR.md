---
id: 01M83S20XAC0HW2AVFDS2XW6SR
module: feature.Spec
entity: ClosedSetCheck
kind: feature
status: active
supersedes:
- 01M83R4D4KHKZE3V588Y9X5DEH
anchors:
- src/pmem/generate/spec_closed.py#_line_heading
- src/pmem/generate/spec_closed.py#_annotation_on_symbol
revision: git:223a61d
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 未知栏目结束上一节；字段签名只对照入口函数
verify: uv run pytest tests/test_spec_closed.py -q
applies: 跑 pmem spec closed 时
aliases:
- 章节串读
- 字段签名误报一致
source:
  conversation: e0ffd8af-3de7-48fb-8ac0-0d832c508a60
  kind: code
---
需求来源：核对器会把不属于当前栏目的后文算进去，也会拿无关函数的同名参数报成一致。
必须保持：closed 仍只读，只出一致 / 可能不一致 / 无法判断，不写规格。
已知栏目是入口、入参字段闭集、出参字段闭集、原文（须按字面抄）、必须保持。同一行可以写成「标题：第一句」，第一句仍属于该节。
Markdown 标题，以及骨架栏目（数据形状与闭集词表、所有权、决定表、失败条件、配置与环境变量、关键流程、生成物、一轮例子、单独拿走时还要带走的依赖规格、会话字段闭集），结束当前节。原文里单独成行、以冒号结尾的句子不是新栏目。
带类型的字段只对照入口里路径#符号指向的函数参数。没有这种入口、符号对不上函数，或入口函数没有这个参数时，不把别的函数的同名注解报成一致。
无类型签名的字段名只出现过仍报无法判断。原文仍先剥一行说明前缀，只在同一文件里按顺序、相邻不超过 4000 字对。
入口：pmem spec closed；src/pmem/generate/spec_closed.py 的 _sections、_one_field。
