---
id: 01M51NZ2Y8SBPH444NYVN46PQE
module: feature.ModuleCatalog
entity: NameMatch
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#name_patterns
revision: git:6d89f59
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 模块识别
- 正文提及
- 误命中
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
决定：识别“一段文字提到了哪个模块”统一用 ModuleRegistry.name_patterns()，记忆图谱的“正文提及”和提问审查共用这一套规则。

规则：
- 只用模块名和不带点的别名；带点的别名本身就是完整 id，单独匹配。
- 英文名至少 4 个字符，按词边界匹配，前后不能紧挨字母、数字或下划线。
- 中文名至少 2 个字。

原因：UI、Ad、Map 这类短英文名会命中 GUI、Admin、Mapping 等无关词，在提问审查里会追问不相干的模块。单字中文名同样容易误命中。

影响：名字太短的模块不会被提问识别出来，只能靠路径、完整 id 或读代码时的摘要覆盖；需要时给它加一个更长的别名。
