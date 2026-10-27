---
id: 01M5EP78A7710PZPFSPVYQ9JT7
module: feature.Gate
entity: Hierarchy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/guard.py
- src/pmem/hooks/review.py
- src/pmem/hooks/memories.py#ancestor_pitfalls
- src/pmem/hooks/memories.py#modules_in_text
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 子模块自己没记忆但上级有教训时也拦截，提示和摘要附上级的坑；提及按完整模块名匹配
verify: uv run pytest tests/test_module_hierarchy.py -k "gate or mentions"
aliases:
- 闸门拦截子模块
- 上级的坑
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:45.340+08:00'
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块设计，用户确认“子模块没有记忆、父模块有教训时，闸门同样拦截”。
必须保持的行为：
- guard：模块自己有记忆，或任一祖先有教训（非 feature/plan）时拦截；提示写“上级模块另有 N 条教训”，坑列表追加最多 2 条祖先教训，标“上级 <模块>/”。
- 读代码摘要（review）同样追加祖先的坑，引语标“（含上级模块的坑）”。
- 按模块检索子模块即算查过该子模块；查父模块不替子模块放行。
- modules_in_text 按完整模块名匹配：前面不能紧挨字母数字下划线点号，后面不能接字母数字下划线或“.字母”，所以“system.Ads.AdMob”不会同时算作提及 system.Ads。
入口：src/pmem/hooks/guard.py、hooks/review.py、hooks/memories.py（ancestor_pitfalls、modules_in_text）。
