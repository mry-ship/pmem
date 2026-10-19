---
id: 01M51PJN7JSW2PJPCPR4FSJ220
module: feature.Gate
entity: GuardPitfalls
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 拦截提示
- 排除项
- 踩坑
- 需核实
verified: '2026-10-19'
---
决定：改代码被拦截时，拦截提示（user_message）里直接列出该模块现行的排除项和风险。
最多列 5 条，超出的写“另有 N 条”，被替代的不列，关联代码之后改过的标“需核实”。
读代码摘要也会标“需核实”，并提示核对后用 confirm_memory 确认，或写 correction 替代。

原因：拦截后 Agent 会调用 search_memory，但检索按关键词和语义排序，只返回前 5 条；
关键词没对上时，与这次修改相关的排除项可能排不进来，坑就漏掉了。
排除项和风险是“改之前最该知道”的两类，数量通常不多，直接放进拦截提示，Agent 一定能看到。
Cursor 只把 user_message 交给 Agent（实测），所以必须写在这里。

风险：排除项很多的模块提示会变长，所以只列 5 条，每条预览 100 字。普通结论和决定仍然要靠检索或读代码摘要获得。
