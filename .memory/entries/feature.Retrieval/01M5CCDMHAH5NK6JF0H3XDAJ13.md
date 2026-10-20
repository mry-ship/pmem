---
id: 01M5CCDMHAH5NK6JF0H3XDAJ13
module: feature.Retrieval
entity: Supersede
kind: decision
status: active
supersedes:
- 01M52HVD0GXQP9MYEJSGF23EG7
anchors:
- src/pmem/core/entry.py#replaces
- src/pmem/index/store.py#superseded
- src/pmem/index/graph.py#current_entries
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 归档记忆仍算替代，唯一例外是撤销过的合并
---
决定（更新替代口径）：归档（archived）记忆的 supersedes 仍然算数，唯一例外是撤销过的合并（YAML 头有 reverted）：它不再替代任何记忆，原记忆重新现行。
原因：归档的语义是“这条连同它那条演进线都已过时”，归档合并产物不能让零碎旧记忆复现；但合并本身做错时需要回到合并前，所以单独加撤销标记，而不是改归档语义。
as_of 回看：撤销日之前的日期仍按替代算（当时原记忆是隐藏的），之后按不替代算；替代关系仍按写入日期生效。
范围：所有计算替代关系的地方统一走 Entry.replaces（检索 superseded、current_entries、doctor、pmem map、断链检查）。
撤销的限制：合并产物已被更新的记忆替代时拒绝撤销，因为撤销后原记忆仍被隐藏；被替代的原记忆本身已归档的不会恢复，返回 not_restored 说明原因。
风险：旧版 pmem 不认 reverted 字段，仍把撤销的合并当替代，原记忆在旧版里还是隐藏的，团队要一起升级。
