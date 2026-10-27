---
id: 01M5CCDXJ6VW29ZYW22PX6V04B
module: feature.Tools
entity: Revert
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/status.py#revert
- src/pmem/service/status.py#change_status
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: revert 撤销合并：归档并标已撤销，原记忆复现；restore 重做
aliases:
- 撤销合并
- 回滚
- undo
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
---
需求来源：用户要求能撤销错误的合并（Issue #13 第 3 项）。
必须保持的行为：
- MemoryService.revert(id)：这条归档（记 archived 的日期、原状态、操作人）并写 reverted: {on, by}，它 supersedes 的原记忆重新现行；
  返回 restored 和 not_restored（找不到、已归档、仍被别的记忆替代各附原因）。
- 拒绝：找不到、已撤销过（提示用 archive --restore 重做）、没有 supersedes（不是合并产物，提示用 archive）、已被更新的记忆替代。
- change_status 的 restore 同时清掉 reverted，等于重做合并。
- 只走命令行 pmem compact --undo，不暴露为 MCP 工具（与 archive 一致）。
入口：src/pmem/service/status.py 的 revert。
