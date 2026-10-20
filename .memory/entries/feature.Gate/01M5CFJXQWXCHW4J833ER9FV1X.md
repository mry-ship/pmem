---
id: 01M5CFJXQWXCHW4J833ER9FV1X
module: feature.Gate
entity: GuardPitfalls
kind: decision
status: active
supersedes:
- 01M51PJN7JSW2PJPCPR4FSJ220
anchors:
- src/pmem/hooks/guard.py#_pitfalls
- src/pmem/hooks/guard.py#_guard_module
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 拦截提示直接列出模块的排除项、风险、更正和该文件的功能记录
aliases:
- 拦截提示
- 排除项
- 踩坑
- 需核实
---
决定：改代码被拦截时，拦截提示（user_message）直接列出该模块现行的排除项、风险和更正（更正：旧记忆只写了排除项和风险），最多 5 条，超出写“（另有 N 条，检索时可见）”，被替代的不列，关联代码之后改过的标“需核实”。
另外附上该文件的功能记录和全项目通用的坑。
原因：拦截后 Agent 检索按关键词和语义排序只返回前几条，关键词没对上时相关排除项可能排不进来；这几类是“改之前最该知道”的，数量通常不多，直接放进提示一定能看到。Cursor 只把 user_message 交给 Agent（实测）。
风险：排除项多的模块提示会变长，所以只列 5 条。更正：每条只显示一行标题（约 60 字），不是“预览 100 字”。
