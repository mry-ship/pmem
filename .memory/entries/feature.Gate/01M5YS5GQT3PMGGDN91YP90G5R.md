---
id: 01M5YS5GQT3PMGGDN91YP90G5R
module: feature.Gate
entity: Digest
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/graph.py#current_entries
- src/pmem/hooks/memories.py#module_entries
- src/pmem/hooks/review.py#_offer_digest
- src/pmem/hooks/guard.py#_pitfalls
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 上级替代下级后，读码摘要和闸门仍把下级旧结论当现行
verify: 父模块 record 并 supersedes 子模块一条排除项；search_memory(module=子模块) 不再返回该 id；读子模块文件的摘要仍出现该标题
applies: '用父模块替代下级记忆，或非全项目级记忆替代了 scope: project 的记忆时'
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
现象：父模块用 supersedes 替代下级记忆后，search_memory 里这条下级记忆消失，但读代码摘要、闸门拦截列出的排除项/风险/更正、以及“现行记忆 N 条”仍把它当现行。
原因：索引 MemoryIndex.superseded 扫全部记忆文件；
Hook 的 module_entries 只读该模块目录下的 *.md，current_entries 只用这一批文件里的 supersedes 判断。
父模块文件不在这批里，下级旧结论不会被隐藏。
全项目级坑（project_entries）同样：替代它的那条若不是 scope: project，也不在这批里。
影响：把兄弟模块的结论提升到父模块并替代后，读子模块代码的 Agent 仍会看到旧结论，并且和继承来的新结论并列。检索本身是对的。
证据：index/graph.py current_entries；
hooks/memories.py module_entries；
hooks/review.py _offer_digest；
hooks/guard.py _pitfalls。
