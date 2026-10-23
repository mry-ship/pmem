---
id: 01M5MBG7AY7462X2KMABEY2G6R
module: feature.Spec
entity: NinetyBar
kind: decision
status: active
supersedes: []
anchors:
- .cursor/skills/pmem-spec/SKILL.md
- src/pmem/generate/templates.py
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 九成分母是已实现对外契约，不是源码行数，也不是未写入的策划稿
verify: 技能含「九成的分母」；各模块程序设计有出参字段闭集和生成物；策划有「已实现行为的策划以代码可见规则为准」
applies: 判断规格是否达到可拿走复用的完成度时
aliases:
- 90%
- 九成
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
选定：补全模块规格有用的验收是「已实现对外契约能从规格还原至少九成」。
分母：入参、出参、词表、数字、对外文案、生成物结构、失败条件。
不计：源码行数、内部函数名、测试夹具、代码里没有的完整策划稿。
策划设计要把代码可见的数值、边界、表现、规则写全，并写「已实现行为的策划以代码可见规则为准」；独立于代码、扫代码也补不回来的稿才留 design-gap。
没选：把 --check 改成判断九成；把技能模板或源码整份粘进规格来凑行数。
