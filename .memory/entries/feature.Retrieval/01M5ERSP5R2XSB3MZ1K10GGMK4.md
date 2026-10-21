---
id: 01M5ERSP5R2XSB3MZ1K10GGMK4
module: feature.Retrieval
entity: Inherit
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#_merge_by_score
- src/pmem/index/store.py#search
- src/pmem/hooks/memories.py#ancestor_pitfalls
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 祖先教训并入结果时不能整体按分数重排；祖先候选截取数要用 max(limit, inherit_max)
verify: uv run pytest tests/test_module_hierarchy.py -k "spare_own or own_limit or
  filed_under_another_name"
aliases:
- 继承
- 上级教训
- 祖先名额
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
坑（2026-10-21 复查父子模块改动时发现）：查子模块时把祖先教训并入本模块结果，第一版有两个问题。
1) 并入后按原始分数整体重排：本模块结果已经过同批降权（同一批超额的排到其他相关结果之后），按原始分数重排会把降权的记忆提回前面，违反 SpreadBatches 更正“名额内须保持原排序”。
   现在两边各自保持降权后的次序，只按分数交错合并。
2) 名额计算没封顶：limit 小于 inherit_max（如 limit=1）时切片下标变负，返回条数乱。后来按用户要求改为祖先在 limit 之外另给，本模块不被挤占，切片问题随之消失。
但祖先候选先经 _spread_batches 截取时，截取数不能只用 limit，否则 limit=1 时只能带回 1 条祖先教训；要用 max(limit, inherit_max)。
同次修正：Hook 里取上级教训排序时按目录对应的祖先层级算距离，不再按记忆正文里的 module 字段查表；手工搬动或改名残留导致两者不一致时原先会 KeyError，Hook 整个失败。
