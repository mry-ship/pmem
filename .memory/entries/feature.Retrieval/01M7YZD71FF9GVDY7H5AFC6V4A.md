---
id: 01M7YZD71FF9GVDY7H5AFC6V4A
module: feature.Retrieval
entity: ReadingOrder
kind: decision
status: active
supersedes: []
anchors: []
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 时效与证据的读法写在检索提示里，不改排序
verify: 普通问答的 search_memory 结果带这条读法；排序与 RULE_BODY 都不变
applies: 要让 Agent 更稳定地使用现有需核实、applies、来源和 verify 时
aliases:
- 阅读顺序
- 检索提示
- 证据读法
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
决定：这套读法写在 search 已经返回的提示里：先处理需核实，再看 applies 是否满足；
多条冲突时优先查看有锚点、有 verify、来源不是 inference 的，其余相关记忆仍要看。
不改排序，不过滤，不写进 RULE_BODY，也不写进 pmem-quality、pmem-minimal、pmem-review。

原因：质量规则只决定何时加载技能，普通问答不加载。写进记忆规则正文会进 bench 的 on 组，把使用方式和记忆内容的价值混在一起。Gate 的问答审查只检查有没有查过模块，不解释时效和来源。

提示加长会进每次检索的 Token，只改短句。现有提示已经足够时，不要为了走完这一步再改文案。
