---
id: 01M52J02DJ260P2N4BHMNZK4DW
module: feature.Tools
entity: Status
kind: decision
status: active
supersedes:
- 01M52HVBYRXH1GR36G9EGW9D8P
anchors:
- src/pmem/service.py#change_status
- src/pmem/service.py#_record
- src/pmem/core/entry.py#status_on
revision: git:2f0f6f6
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 归档
- 恢复
- 转正
- 退回
- archive
- restore
verified: '2026-10-19'
---
决定：记忆状态的变更集中在 MemoryService.change_status，只允许四种动作：archive（active/seed/draft → archived）、restore（archived → 归档前的状态，没记录时 active）、accept（seed → active）、reject（seed → archived）。
归档时在 YAML 头记 archived: {on: 日期, from: 原状态}，恢复后清掉；
正文、id、替代关系不变。
状态不符的条目放进 skipped 返回。
这些动作只走命令行（pmem archive / pmem seed），不暴露为 MCP 工具。

记原状态的原因：原先 restore 一律回到 active，被退回的种子恢复后会绕过负责人确认直接变成正式记忆。

record：status 只接受 active/seed/draft；
用 draft_id 覆盖时没传 status 则沿用草稿原状态；
写入废弃模块直接拒绝；
不能用 draft_id 覆盖已归档的记忆（否则会被悄悄恢复成正式记忆），提示先 restore 或新建替代；
supersedes 里包含 draft_id 本身时忽略 draft_id、按新建处理（草稿已提交后闸门仍会按同议题注入 draft_id，原先这种写入只能一直失败）。
写入被拒绝时记本机事件 record_rejected，供 pmem health 统计。

风险：加 archived 字段之前归档的文件，恢复后一律是 active；MCP 服务是常驻进程，改了 service 代码要重启才生效。
