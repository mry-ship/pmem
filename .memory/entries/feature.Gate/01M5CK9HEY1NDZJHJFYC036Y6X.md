---
id: 01M5CK9HEY1NDZJHJFYC036Y6X
module: feature.Gate
entity: StopReminder
kind: correction
status: active
supersedes:
- 01M59Y4E0BHPG0E6342WZAFRW7
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/review.py#_unreviewed
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 结束提醒去掉“自动发给 AI 的提醒”标头行，每条仍以 [pmem] 开头
verify: uv run pytest tests/hooks/test_gate.py -k stop_reminds_once
aliases:
- 结束提醒
- 标头
- followup
- 自动提醒
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
更正（2026-10-20）：旧决定在结束提醒第一行加“[pmem] 以下是 pmem 自动发给 AI 的提醒，由 AI 处理，你无需操作。”，用户反馈每次都来一条很烦，要求去掉。
现在：followup_message 只含各条提醒本身，每条都以 [pmem] 开头；解释“这是给 AI 的、不用你处理”改放在规则模板（告诉 AI 直接处理、不向用户确认）和 README/手册里。
仍成立：第一行必须以 [pmem] 开头——review.py 的 _unreviewed 靠“最后一条用户消息以 [pmem] 开头”认出这是自动提醒，新增提醒类型时也要带这个前缀，否则闸门会把提醒当成新问题再追问一轮。
数据：近 3 天 66 个回合里只有 4 次带结束提醒（改了没写 3 次、提问没查 1 次）。
