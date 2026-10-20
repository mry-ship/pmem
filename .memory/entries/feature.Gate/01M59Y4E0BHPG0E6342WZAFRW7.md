---
id: 01M59Y4E0BHPG0E6342WZAFRW7
module: feature.Gate
entity: StopReminder
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#FOLLOWUP_HEADER
- src/pmem/hooks/gate.py#on_stop
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 结束提醒
- 要我自己写吗
- 自动提醒像用户消息
- followup
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：回合结束时的提醒（改了代码没写记忆、没核对记忆、闸门出错通知）第一行固定加上 FOLLOWUP_HEADER：“[pmem] 以下是 pmem 自动发给 AI 的提醒，由 AI 处理，你无需操作。”
原因：Cursor 把 followup_message 显示成一条用户消息，用户看到“请直接用 record_memory 为每个模块写一条”会误以为要自己写原因（2026-10-19 实际发生）。实际上写入由 AI 完成，用户不用参与。
影响：Cursor 的 followup_message 和 Claude/Codex 的 Stop reason 都带这一行。
注意：说明行必须以 [pmem] 开头——下一轮 _unreviewed 靠“最后一条用户消息以 [pmem] 开头”认出这是自动提醒、不是用户提问，改掉会让闸门把提醒当成新问题再追问一轮。
