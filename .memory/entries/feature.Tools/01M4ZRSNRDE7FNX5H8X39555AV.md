---
id: 01M4ZRSNRDE7FNX5H8X39555AV
module: feature.Tools
entity: Terms
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/service/curation.py#terms
revision: git:bfe2969
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 高频词
- 词表不稳定
- 结果随机
- PYTHONHASHSEED
verified: '2026-10-19'
---
结论：pmem terms（高频词统计）原先每次运行结果不稳定：计数相同的词谁排前面会变，取前 N 个时边界附近的词会进进出出。

原因：每条记忆的分词结果放在 set 里再逐个计数，Counter.most_common 遇到同票按插入顺序排，而 set 的遍历顺序取决于字符串哈希，Python 每个进程的哈希种子（PYTHONHASHSEED）都是随机的。

证据：同一份代码对本仓库连跑两次 terms(module=feature.Gate, top=30)，词和计数的多重集合一致，但第 30 名附近的词不同。

处理：计数前先对每条记忆的词排序，同票词按“记忆顺序 + 字典序”固定；计数本身不变。pmem-normalize 技能依赖这份词表起草同义词组，结果不稳定会让两次起草对不上。

另：本次重构 service / store / gate 后，用 git worktree 取出改动前的代码，对本仓库真实记忆跑同一批 19 组调用（search 各种组合、graph、terms、list、compact、record 的校验失败路径）逐项比对 JSON，除 terms 外完全一致；
以后做“行为不变”的重构可以照此验证。
