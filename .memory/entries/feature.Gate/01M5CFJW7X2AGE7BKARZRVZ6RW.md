---
id: 01M5CFJW7X2AGE7BKARZRVZ6RW
module: feature.Gate
entity: PromptReview
kind: decision
status: active
supersedes:
- 01M51NT6KBHR112A1Y5EWTMQGF
anchors:
- src/pmem/hooks/gate.py#_offer_digest
- src/pmem/hooks/gate.py#_unreviewed
- src/pmem/hooks/gate.py#on_stop
- src/pmem/index/graph.py#digest
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 问答也做记忆审查：提问时（Claude/Codex）、读代码时、回合结束时三层
aliases:
- 问答审查
- 记忆审查
- 读码摘要
- additional_context
---
决定：不改代码的问答也做记忆审查，分三层；同一模块一个对话只触发一次（reviewed 记录，search_memory 查过、看过摘要都算）。
1. 提问时：Claude Code 和 Codex 的 UserPromptSubmit 直接返回 additionalContext，附问题提到的模块摘要（更正：旧记忆只写了 Claude）。
   Cursor 的 beforeSubmitPrompt 只能放行或拦截，只记进 asked。
2. 读代码时：postToolUse 把文件所属模块的现行教训摘要放进 additional_context，按排除项、风险、更正、决定、结论排序，每议题最多 2 条，共 6 条；
   锚点在当前文件的排前面；
   功能记录不占名额，末尾另附至多 2 条本文件的功能记录。
   更正：每条只显示一行标题（summary 或首句，截到 60 字），不是“预览 100 字”。
3. 回合结束时：stop 从 transcript_path 读本轮提问原文，按完整模块 id、模块名或别名（英文≥4 字符按词边界、中文≥2 字）、路径映射识别模块；
   有记忆却没进 reviewed 时用 followup 要求先查再核对，最多 3 个模块。
   loop_count>0、stop_hook_active、中断结束、已追问过的不追问。
开关：gate.read_digest 和 gate.question_review，默认都开。
实测（Cursor/Windows）：读 cite.py 时摘要以 system_reminder 出现在工具结果末尾。
没选：显式 [[模块#议题]] 互链，模块关系由 memory_graph 自动推导。
