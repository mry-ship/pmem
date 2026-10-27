---
id: 01M5CFJCC6ZS9KJM8YHMBA55NZ
module: feature.Tools
entity: Status
kind: decision
status: active
supersedes:
- 01M52J02DJ260P2N4BHMNZK4DW
anchors:
- src/pmem/service/status.py#change_status
- src/pmem/service/status.py#revert
- src/pmem/service/record.py#_record
- src/pmem/core/entry.py#status_on
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 状态变更走 change_status 四种动作，另有 compact --undo 撤销合并
aliases:
- 归档
- 恢复
- 转正
- 退回
- archive
- restore
- 撤销合并
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
决定：记忆状态变更主要走 MemoryService.change_status 的四种动作：archive（active/seed/draft → archived）、restore（回到归档前的状态，没记录时 active）、accept（seed → active）、reject（seed → archived）。
归档时 YAML 头记 archived: {on, from, by}，恢复后清掉（同时清 reverted）；
正文、id、替代关系不变；
状态不符的放进 skipped。
只走命令行，不暴露为 MCP 工具。
更正：不再“只有四种动作”。pmem compact --undo 走 MemoryService.revert，不经 change_status，直接把合并结果归档并写 reverted，被它替代的旧记忆恢复可见。
记原状态的原因：原先 restore 一律回到 active，被退回的种子恢复后会绕过负责人确认。
record：status 只接受 active/seed/draft；
draft_id 覆盖没传 status 沿用原状态；
写入废弃模块拒绝；
不能用 draft_id 覆盖已归档的记忆；
supersedes 含 draft_id 本身时按新建处理；
被拒时记 record_rejected。
风险：加 archived 字段之前归档的文件恢复后一律 active；MCP 服务常驻，改了 service 代码要重启。
