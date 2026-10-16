---
id: 01M52HVD0GXQP9MYEJSGF23EG7
module: feature.Retrieval
entity: Supersede
kind: decision
status: active
supersedes:
- 01M52G77VHWZBPDJ7VGM2ARB1B
anchors:
- src/pmem/index/store.py#superseded
- src/pmem/index/store.py#_visible_items
- src/pmem/core/entry.py#status_on
- src/pmem/index/graph.py#current_entries
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 替代
- 归档
- 历史视角
- as_of
- supersedes
---
决定：计算“已被替代”的记忆集合时，归档（archived）记忆的 supersedes 也算数；归档记忆本身照旧不出现在检索里。

原因：归档的语义是“这条结论连同它那条演进线都已过时”。如果只按 active/seed/draft 计算替代关系，归档一条合并后的记忆，它当初替代的零碎旧记忆会全部重新变成现行。

范围：MemoryIndex.superseded、记忆图谱的 current_entries 与 superseded_by、doctor 的现行条数，三处口径一致（REPLACING_STATUSES / REPLACING）。

as_of 回看：按 Entry.status_on(日期) 判断可见性，归档日期晚于回看日的按归档前的状态算（当时还是现行）；没有归档日期的旧文件一律按已归档。替代关系仍按写入日期算。

风险：想“撤销一次错误的合并”时，归档合并记忆做不到，需要 pmem archive --restore 恢复它后再写一条新的替代；种子转正没有记日期，as_of 回看时看到的是当前状态。
