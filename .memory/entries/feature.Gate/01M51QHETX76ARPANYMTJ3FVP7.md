---
id: 01M51QHETX76ARPANYMTJ3FVP7
module: feature.Gate
entity: SkipNotice
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_skip_notice
- src/pmem/hooks/gate.py#on_prompt
- src/pmem/hooks/gate.py#_guard
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 跳过记忆
- 恢复记忆
- 误跳过
---
决定：“跳过记忆”生效后要让人看得见，并且能撤销。

现象：之前误触发“跳过记忆”时，整个对话静默关闭记忆：读代码不附摘要、改代码不拦、结束不提醒，用户和 Agent 都不知道。

现在：
- 记下触发它的提问片段（前后约 12 个字，Windows 乱码时用还原后的原文）；
- 本对话第一次读代码时，通过 postToolUse 附一次说明：记忆已关闭、来自哪句提问、如非本意让用户说“恢复记忆 / resume-memory”（gate.resume_markers 可配）；
- 用户说恢复后清除 skip、原因和“已提示”标记，之后照常查、拦、提醒。

另外，拦截提示里列出的“坑”从排除项、风险扩展到更正（correction），按排除项、风险、更正排序，最多 5 条。更正往往说明旧结论是错的，改代码前最需要看到。
