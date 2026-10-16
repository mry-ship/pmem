---
id: 01M51QHJ9RP5WE878MPA430ZPN
module: infra.Model
entity: Config
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 恢复记忆
- resume
---
决定：配置新增 gate.resume_markers，默认 ["恢复记忆", "resume-memory"]。用户在已“跳过记忆”的对话里说出其中之一，就撤销本对话的跳过，恢复检索、拦截和提醒。匹配规则与 skip_markers 相同（独立短语才算，兼容 Windows 乱码还原）。config.yaml 模板里以注释形式列出两项，方便团队改成自己的说法。
