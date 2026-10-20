---
id: 01M5CQ7NNWERRZ4FXW22ZD3CJ9
module: feature.Retrieval
entity: SpreadBatches
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_spread_batches
- src/pmem/index/anchors.py#AnchorChecker._worktree_state
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 同一作者同一模块 90 分钟内算一批（连续窗口，非固定时间桶）
verify: uv run pytest tests/index/test_index.py -k batch
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，审查复现：“同一批最多 2 条”原先按 created // 90 分钟的固定时间桶切，跨过桶边界的 3 条磎碎记忆会全部返回，与文档“90 分钟内”不符。
必须保持：没有对话 id 的记忆按作者+模块按时间连续成段，与这一段第一条相隔 90 分钟以内的算同一批；有对话 id 的仍按对话分批。
同时：过期核对的跨进程缓存指纹只排除 .memory/entries/（记忆文件每次写入都变），.memory/config.yaml、modules.yaml 的未提交改动要让缓存失效，它们也可能是锚点。
入口：index/store.py 的 _spread_batches、index/anchors.py 的 AnchorChecker._worktree_state。
