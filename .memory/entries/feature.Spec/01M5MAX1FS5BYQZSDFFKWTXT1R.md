---
id: 01M5MAX1FS5BYQZSDFFKWTXT1R
module: feature.Spec
entity: FieldClosedSet
kind: exclusion
status: active
supersedes: []
anchors:
- .memory/specs/feature.Gate/程序设计.md
- .memory/specs/feature.Tools/程序设计.md
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 排除：用散文入口或协议大意代替入参字段闭集
verify: 各模块程序设计.md 含「入参字段闭集」与「原文（须按字面抄）」；模块现状.md 含「单独拿走时还要带走的依赖规格」
applies: 写或审规格程序节与现状节时
aliases:
- 读一份 JSON
- 转述
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
排除：入口只写「标准输入读 JSON」或「有若干参数」，不列字段名、缺省和非法时怎样。
排除：把其它程序会解析的键名、用户必须原样打出的标记、发给 Agent 且下一轮还要再认的固定句转述成大意。
证据：对 14 个模块只读规格反推时，Gate 推不出 stdin 字段闭集，Tools 推不出 search_memory 参数表，全部缺依赖规格命名清单。
处理：这三类都当缺口，打开代码只为按字面抄进规格。
没选：让 --check 去读懂正文是否可重做。
