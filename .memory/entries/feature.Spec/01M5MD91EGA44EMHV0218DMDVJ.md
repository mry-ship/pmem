---
id: 01M5MD91EGA44EMHV0218DMDVJ
module: feature.Spec
entity: NinetyBar
kind: correction
status: active
supersedes:
- 01M5MBG7AY7462X2KMABEY2G6R
anchors:
- src/pmem/generate/templates.py
- src/pmem/generate/spec.py#_bodies
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 补全规格有用的验收改为已实现对外契约至少九成八
verify: 技能含「九成八的分母」；骨架含失败条件、配置与环境变量；complete 标准输出含九成八
applies: 判断规格是否达到可拿走复用的完成度时
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
更正：旧决定把补全模块规格的验收定为九成。用户随后要求九成八。
选定：已实现对外契约能从规格还原至少九成八才算有用。
分母仍是入参、出参、词表、数字、对外文案、生成物结构、失败条件，并加上配置键和环境变量。
不计：源码行数、内部函数名、测试夹具、代码里没有的完整策划稿。
新缺口：原文写成「含某某」而不是带尖括号占位的模板全文；失败条件只写「返回非零」；配置键和环境变量不列闭集。
没选：把 --check 改成判断九成八；把技能模板或源码整份粘进规格来凑行数。
