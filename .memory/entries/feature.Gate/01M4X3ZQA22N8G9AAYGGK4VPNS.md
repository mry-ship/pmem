---
id: 01M4X3ZQA22N8G9AAYGGK4VPNS
module: feature.Gate
entity: Payload
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#on_pre_tool
revision: git:e258c6e
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
Cursor 3.9 Hook 输入实测：所有事件都带 conversation_id（与 session_id 相同）和 workspace_roots（形如 /c:/Users/...，需去掉开头斜杠）；
Hook 进程工作目录就是工作区根。
StrReplace 在 preToolUse 里显示为 tool_name=Write，tool_input.content 是修改后的全文；
终端命令为 tool_name=Shell，tool_input.command，cwd 常为空字符串。
hooks.json 的 matcher 按 tool_name 正则过滤有效（Write|Shell 只匹配这两类）。
stop 返回的 followup_message 会作为一条新的用户消息自动提交给 Agent，可用于结束提醒。
Hook 配置修改后在当前对话中即时生效，无需重启。
