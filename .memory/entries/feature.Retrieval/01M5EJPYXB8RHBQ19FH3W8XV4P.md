---
id: 01M5EJPYXB8RHBQ19FH3W8XV4P
module: feature.Retrieval
entity: Ranking
kind: conclusion
status: active
supersedes:
- 01M5CJXZ80NA1QYVM3JG82ZQ6R
- 01M5CX3QCMN4WYB55Z8Y488964
anchors:
- scripts/eval_real_queries.py#run
- scripts/eval_real_queries.py#build_known
- src/pmem/index/store.py#_spread_batches
- scripts/eval_real_queries.py
- README.md
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 检索效果现行数字：真实题前三 90%、按文件前三 98%、换说法前三 97%
verify: uv run python scripts/eval_real_queries.py
aliases:
- 检索效果
- 召回率
- 命中率
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
---
结论：检索效果用 scripts/eval_real_queries.py 三套题回放，现行数字（2026-10-20 晚，本仓库现行记忆，语义加关键词）：
- 真实检索 91 题：排第一 40/91（44%）、前三 82/91（90%）、MRR 0.657；仅关键词前三 73/91（80%）、MRR 0.610。
- 按文件 120 题（只传 path）：排第一 113/120（94%）、前三 118/120（98%）、MRR 0.967。
- 别名已登记且不在正文里的 126 题：排第一 103/126（82%）、前三 122/126（97%）、MRR 0.892。
这三行已写进 README 效果一节和手册收益表。

口径：真实题的答案是当时回复确实用到的记忆，衡量现在还能不能把那条结论排回来，不是绝对召回率。
按文件题由锚点生成，与加分规则同源；
更早在记忆库副本上重放 v0.2 时按文件前三是 100%，只证明规则生效，现行库变大后是 118/120，不要再把 100% 写进主页。
版本对比（副本重放）：按文件题 v0.2 发布前三 45% → 引入按文件加分后 100%；
别名删掉后的换说法题 v0.2 前三 72% → 当前 76%（标题、验证方法进索引后的提升）。
真实题当时少的 3 题都是 Embedding 决定 01M4X40BBTRXTJT8KJS5DJ3AB0 被“同一批最多 2 条”整条剔除（见 SpreadBatches 风险）。
坑：as_of 只到天，要按 ULID 时间去掉检索之后才写的记忆；事件日志里的中文查询大量乱码，抽题时还原或丢弃；重放旧版本用记忆库副本，避免写坏向量缓存；用 --ranks 逐题对比两个版本。
未测：改代码质量的端到端对比。合并自 2 条记忆。
