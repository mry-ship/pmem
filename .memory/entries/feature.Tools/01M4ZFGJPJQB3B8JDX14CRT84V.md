---
id: 01M4ZFGJPJQB3B8JDX14CRT84V
module: feature.Tools
entity: Similar
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/service.py#_similar_memories
revision: git:fc9f6d8
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 相近记忆
- Mem0
- 去重
- 规整
---
排除：写入时返回“相近记忆”（similar，借鉴 Mem0 的 ADD/UPDATE 判断）不能按相关度阈值跨实体去找。试过之后，几乎每次写入都会带回同模块里其他议题的无关记忆，Agent 反而容易误判成要更新旧记忆。这也和之前检索排序的结论一致：相关度分数没有可靠的绝对阈值。

现在的做法：只返回同模块、同实体（不分大小写）的有效记忆，最多 2 条，附上 id、日期、kind 和摘要。提示语要求 Agent 判断：同一结论的补充就带 draft_id 覆盖；推翻旧结论就新写一条并填 supersedes；确实是新信息就保留。

“规整”由写入的 Agent 自己完成（它本身就是大模型），pmem 不调用外部大模型 API：
- 规则要求把现象的其他叫法写进 aliases，缺了会提示；
- 团队通用的同义叫法由 pmem-normalize 技能根据 pmem terms 的高频词起草，用户确认后写入 modules.yaml 的 synonyms。
