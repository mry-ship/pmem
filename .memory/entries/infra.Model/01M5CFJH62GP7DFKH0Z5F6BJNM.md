---
id: 01M5CFJH62GP7DFKH0Z5F6BJNM
module: infra.Model
entity: Config
kind: decision
status: active
supersedes:
- 01M51QHJ9RP5WE878MPA430ZPN
anchors:
- src/pmem/core/config.py#DEFAULTS
- src/pmem/hooks/gate.py#on_prompt
- src/pmem/generate/templates.py#CONFIG_TEMPLATE
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: gate.resume_markers 默认 恢复记忆/resume-memory，撤销本对话的跳过
aliases:
- 恢复记忆
- resume
---
决定：配置 gate.resume_markers，默认 ["恢复记忆", "resume-memory"]。
用户在已“跳过记忆”的对话里说出其中之一，就撤销本对话的跳过，恢复检索、拦截和提醒。
匹配规则与 skip_markers 相同（独立短语才算，兼容 Windows 乱码还原）。
更正：config.yaml 模板里这两项是生效的配置行（行尾带说明注释），不是“以注释形式列出”；团队改成自己的说法直接改值即可。
