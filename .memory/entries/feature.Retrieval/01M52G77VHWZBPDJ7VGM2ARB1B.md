---
id: 01M52G77VHWZBPDJ7VGM2ARB1B
module: feature.Retrieval
entity: Supersede
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#superseded
- src/pmem/index/graph.py#current_entries
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 归档
- archive
- 替代关系
- 旧记忆复活
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：计算“已被替代”的记忆集合时，归档（archived）记忆的 supersedes 也算数；归档记忆本身照旧不出现在检索里。

原因：归档的语义是“这条结论连同它那条演进线都已过时”。如果只按 active/seed/draft 计算替代关系，归档一条合并后的记忆，它当初替代的零碎旧记忆会全部重新变成现行，检索里突然冒出一堆旧的阶段结论，且不易察觉。

范围：MemoryIndex.superseded、记忆图谱的 current_entries 与 superseded_by、doctor 的现行条数，三处口径一致（REPLACING_STATUSES / REPLACING）。议题时间线里旧记忆会显示 superseded_by 指向已归档的那条。

风险：想“撤销一次错误的合并、让旧记忆恢复”时，归档合并记忆做不到，需要 pmem archive --restore 恢复它后再写一条新的替代，或直接改回旧记忆。
