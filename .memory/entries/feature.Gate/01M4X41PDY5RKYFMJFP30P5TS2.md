---
id: 01M4X41PDY5RKYFMJFP30P5TS2
module: feature.Gate
entity: Output
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_guard
revision: git:e258c6e
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
Cursor 3.9 preToolUse 返回 permission=deny 时，Agent 收到的是 user_message（作为工具报错文本，并附带“不要建议绕过”的说明），agent_message 不会传给 Agent。因此闸门的可执行指引（该调用哪个 search_memory、检索后重试）必须完整写在 user_message 里，否则 Agent 只知道被拦、不知道怎么办。

stop 返回的 followup_message 能完整送达（含中文，Hook 输出用 \u 转义的纯 ASCII JSON），会作为新一轮用户消息触发 Agent。

证据：本仓库自举试用时，修改 tests/hooks/test_gate.py 被拦，Agent 只看到“pmem：修改 feature.Gate 前先检索记忆”；hooks.log 中同一次输出确有 agent_message。warn 档“首次拒绝、重试放行”行为符合预期。
