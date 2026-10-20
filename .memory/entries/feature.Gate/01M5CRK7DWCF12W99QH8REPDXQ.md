---
id: 01M5CRK7DWCF12W99QH8REPDXQ
module: feature.Gate
entity: LayeredDigest
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/memories.py#MemoryView._stale_footer
- src/pmem/hooks/memories.py#MemoryView.fill_stale
- src/pmem/hooks/review.py#Review._offer_digest
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 读码摘要只标“⚠ 需核实”，核对说明每个对话给一次，压缩后再给
verify: uv run pytest tests/hooks/test_gate.py -k "code_is_gone or session_lock"
aliases:
- 读码摘要
- 需核实
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求在功能不变的前提下精简提示，减少每回合占用的上下文。
必须保持：
1) 读代码、搜索时附的摘要里，关联代码改过的记忆只标“（⚠ 需核实）”，不再列改了哪个文件、函数和日期；明细由 search_memory 结果的 check 给出。
2) “需核实怎么处理”（confirm_memory / correction）的说明每个对话只给一次，上下文压缩后重置（state 字段 stale_explained）。该字段在会话锁释放后重新加锁读写，不能在锁外直接保存。
3) 摘要开头缩成“现行记忆 N 条，回答或修改前先看”。拦截时的拒绝消息内容不变。
入口：hooks/memories.py 的 memory_lines、fill_stale，hooks/review.py 的 _offer_digest。
