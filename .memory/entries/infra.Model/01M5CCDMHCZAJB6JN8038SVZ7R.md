---
id: 01M5CCDMHCZAJB6JN8038SVZ7R
module: infra.Model
entity: Revert
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#replaces
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 撤销合并字段 reverted；替代关系统一由 Entry.replaces 计算
---
需求来源：用户要求 v0.3.2 能撤销一次错误的合并（GitHub Issue #13 第 3 项），原先归档合并产物不会让原记忆复现。
必须保持的行为：
- 记忆 YAML 头可选字段 reverted: {on, by}，由 pmem compact --undo 写入，pmem archive --restore 清除（即重做合并）；已加入 KNOWN_KEYS。
- Entry.replaces(day) 是“这条记忆替代了谁”的唯一口径：状态不在 REPLACING_STATUSES 返回空；已撤销且撤销日不晚于 day（day 为空表示现在）也返回空；其余返回 supersedes。
- 检索的 superseded、记忆图谱的 current_entries、doctor 的现行条数、pmem map、断链检查都用它，新增计算替代关系的地方也必须用它，不要再直接读 supersedes。
入口：src/pmem/core/entry.py 的 Entry.replaces。
