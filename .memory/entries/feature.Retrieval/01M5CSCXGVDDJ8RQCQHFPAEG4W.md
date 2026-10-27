---
id: 01M5CSCXGVDDJ8RQCQHFPAEG4W
module: feature.Retrieval
entity: SpreadBatches
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_spread_batches
- src/pmem/index/store.py#search
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 同批超额的记忆只降权：排在其他相关结果之后、不相关之前，不剔除
applies: 检索结果截取前；相关=关键词命中或锚点挨着当前文件
aliases:
- 批次名额
- 碎片记忆
- 多样性
- 降权
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
---
需求来源：用户 2026-10-20 选定“只降权”：同一批（同一对话，或同一作者同一模块 90 分钟内）超出 max_per_batch 的记忆不再整条剔除，而是排到其他相关结果之后、仍排在完全不相关的记忆之前；
既避免碎片挤占名额，也不把相关记忆丢掉。
必须保持的行为：
- 名额内的记忆保持按分数的原排序，不因“相关/不相关”重新分组；超额且相关的插在名额内最后一条相关结果之后，超额且不相关的放在最末。
- “相关”只认关键词 BM25 > 0（含同义词扩展）或锚点挨着当前文件（anchor_affinity > 0），不用语义分：语义分几乎总大于 0，与无关记忆重叠（见 Ranking 排除项）。
- 教训和功能记录两组各自降权，互不挤占。limit 为 0 时返回空。
入口：search 里算出 related 集合传给 _spread_batches。
