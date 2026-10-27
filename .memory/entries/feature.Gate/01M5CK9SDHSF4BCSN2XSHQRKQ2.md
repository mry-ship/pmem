---
id: 01M5CK9SDHSF4BCSN2XSHQRKQ2
module: feature.Gate
entity: StopReminder
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#on_stop
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 结束提醒不加给用户看的标头行，每条以 [pmem] 开头
verify: uv run pytest tests/hooks/test_gate.py -k stop_reminds_once
aliases:
- 结束提醒
- 标头
- followup
verified: '2026-10-27'
verified_at: '2026-10-27T15:48:07.123+08:00'
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户（2026-10-20）觉得“[pmem] 以下是 pmem 自动发给 AI 的提醒……”每次都来一条很烦，要求去掉，由 AI 自己处理。
必须保持：
- followup_message 只拼各条提醒（改了没写、只查没写、提问涉及的模块没查、Hook 出错），不加标头行。
- 每条提醒都以 [pmem] 开头，下一轮靠它认出是自动提醒。
入口：hooks/reminders.py 的 on_stop。
