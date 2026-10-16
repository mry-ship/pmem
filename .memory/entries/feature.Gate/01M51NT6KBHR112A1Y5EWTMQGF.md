---
id: 01M51NT6KBHR112A1Y5EWTMQGF
module: feature.Gate
entity: PromptReview
kind: decision
status: active
supersedes:
- 01M51MYQWYQ2X05T5VDZVMG1J8
anchors:
- src/pmem/hooks/gate.py
- src/pmem/hooks/payload.py
- src/pmem/index/graph.py
revision: git:1acd957
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 问答审查
- 记忆审查
- 读码摘要
- additional_context
---
决定：不改代码的问答也做记忆审查，分三层。同一模块在一个对话里只触发一次，用会话状态里的 reviewed 记录（search_memory 查过、看过摘要都算）。

1. 提问时：Claude Code 的 UserPromptSubmit 直接返回 additionalContext，附上问题提到的模块的摘要。
   Cursor 的 beforeSubmitPrompt 只能放行或拦截，所以只把提到的模块记进 asked。
2. 读代码时：postToolUse 匹配 Read，把该文件所属模块的现行结论摘要放进 additional_context。排序依次为排除项、风险、更正、决定、结论；每个议题最多 2 条，共 6 条，每条预览 100 字。
3. 回合结束时：stop 从 transcript_path 读本轮提问的原文（UTF-8，不受 GBK 乱码影响），识别其中提到的模块。
   识别方式有三种：完整模块 id；
   模块名或不带点的别名（英文至少 4 个字符并按词边界，中文至少 2 个字）；路径映射。
   这些模块有记忆、却没进 reviewed 时，用 followup_message 要求先 search_memory 再核对回答，最多列 3 个模块。
   以下情况不追问：loop_count>0、stop_hook_active、中断结束，以及已追问过的模块（review_nudged）。

开关：gate.read_digest 和 gate.question_review，默认都开。

实测（Cursor，Windows，本仓库）：给 postToolUse 加 matcher "Read" 后，读 src/pmem/metrics/cite.py 时 feature.Metrics 的摘要以 system_reminder 的形式出现在 Agent 看到的工具结果末尾，说明 additional_context 能送达，matcher 也生效。

没选的方向：显式的 [[模块#议题]] 互链。模块关系由 memory_graph 根据共享代码和正文提及自动推导；pmem wiki 生成的页面只供人浏览，不进版本库，以免与记忆本身不一致。
