---
id: 01M5MAWMM11A1ZEGEF32M70SEQ
module: feature.Spec
entity: VerbatimCopy
kind: conclusion
status: active
supersedes: []
anchors:
- .cursor/skills/pmem-spec/SKILL.md
- src/pmem/generate/templates.py
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 反推失败常因入口只写「读 JSON」、协议只写大意
verify: 任取一模块四份规格，不看代码，能读出入参字段名、原文键名或标记、依赖模块名或「无」
applies: 判断补全后的规格能不能单独拿走重做时
aliases:
- 按字面抄
- 入参字段闭集
- 转述算缺口
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
现象：合上代码只凭已填规格重做时，能讲清流程，但推不出 Cursor/Claude 的字段名、MCP 工具参数表、跳过标记原文、依赖要带走哪些模块目录。
根因：写正文的人把「标准输入读 JSON」当作入口，把 permission 为 allow 这类键名转述成大意，依赖只写在所有权叙事里。
这些都是「一样」要求的契约，转述后单独拿走做不出一样的实现。
影响：补全模块规格的机制必须把入参字段闭集、须按字面抄的原文、依赖规格列成停手条；缺一条就回去补，不要停。
策划或美术仍留空的部分仍不能声称那一部分一样。
