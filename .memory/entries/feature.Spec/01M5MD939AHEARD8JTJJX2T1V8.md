---
id: 01M5MD939AHEARD8JTJJX2T1V8
module: feature.Spec
entity: PhraseContains
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- .memory/specs/feature.Gate/程序设计.md
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 排除：用「含某某」代替对外文案模板全文
verify: 技能停手清单含「含某某」；Gate 程序设计原文是带尖括号的全文模板
applies: 写或审规格程序节的原文栏时
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
排除：原文栏写成「结束未查含：这些模块已有研发记忆」这类摘要，不抄带占位的整句模板。
证据：合上代码按九成规格反推时，能说出提醒种类，但拼不出闸门 deny、结束 followup、doctor 收尾行的固定字和尖括号占位，单独拿走做不出一样的对外文案。
处理：固定字按字面抄；会变的部分用尖括号写出，如 <模块>。整句写成「含某某」算缺口。
没选：把源码或技能模板整份粘进规格。
