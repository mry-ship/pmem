---
id: 01M5CJXZ80NA1QYVM3JG82ZQ6R
module: feature.Retrieval
entity: Ranking
kind: conclusion
status: active
supersedes: []
anchors:
- scripts/eval_real_queries.py#run
- scripts/eval_real_queries.py#build_known
- src/pmem/index/store.py#_spread_batches
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 三套题对比：按文件检索 v0.2 仅 18%→100%；未登记叫法语义略好；真实题因分批小幅回退
verify: uv run python scripts/eval_real_queries.py run --set path；--set alias；--set
  real（加 --keyword 对照）
aliases:
- 检索评测
- 评测集
- eval
- top1
- MRR
- 版本对比
- 按文件检索
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
结论（2026-10-20）：scripts/eval_real_queries.py 三套题，记忆库副本上重放 v0.2 发布（df9b06c）、v0.2 末（627b54f，引入按文件加分）、当前。
数字为排第一 / 前三 / MRR，语义＋关键词：
- 真实检索 91 题：44%/90%/0.655 → 44%/90%/0.655 → 44%/87%/0.646。仅关键词 41%/81% → 41%/78%。
- 按文件 120 题（只传 path，答案是锚点在该文件的教训）：18%/45%/0.325 → 100%/100%/1.0 → 100%。题目由锚点生成，与加分规则同源，只证明规则生效。
- 换说法 129 题（查询词是不在正文里的别名）：别名已登记时各版 82%~84%/97%~98%；从副本删掉该别名后 v0.2 42%/72%/0.575，当前 47%/76%/0.605（标题、验证方法进索引后的提升）。
当前真实题前三少了 3 题：都是 Embedding 决定 01M4X40BBTRXTJT8KJS5DJ3AB0 被“同一批最多 2 条”整条剔除（见 SpreadBatches 风险）。
坑：as_of 只到天，要按 ULID 时间去掉检索之后才写的记忆；事件日志里的中文查询大量乱码，抽题时还原或丢弃；重放旧版本用记忆库副本，避免写坏向量缓存；用 --ranks 逐题对比两个版本。
