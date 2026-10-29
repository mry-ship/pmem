---
id: 01M640J0EW6WQYESTWJVW47HK9
module: feature.Gate
entity: RecordedWritten
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#_modules_of_recorded_ids
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: written 类型不对会重置成空 dict，要用 recorded id 认模块
---
根因：会话状态 written 默认是 dict；文件里若是 list（损坏或旧格式），按字段类型丢弃，重置成 {}。recorded 仍是 id 列表，能对上条目文件的模块应视为本对话已写过，否则长对话会反复催已经写过的模块。
