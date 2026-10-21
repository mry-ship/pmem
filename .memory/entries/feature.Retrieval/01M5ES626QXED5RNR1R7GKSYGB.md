---
id: 01M5ES626QXED5RNR1R7GKSYGB
module: feature.Retrieval
entity: Inherit
kind: feature
status: active
supersedes:
- 01M5EP6VWJVM5EBMDCEYAPS3VP
anchors:
- src/pmem/index/store.py#search
- src/pmem/index/store.py#_merge_by_score
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 查子模块时上级教训在本模块 limit 之外另给（默认 2 条，本模块不足时补满），不继承功能记录
verify: uv run pytest tests/test_module_hierarchy.py -k "inherit or own_limit or spare_own"
aliases:
- 继承
- 上级教训
- 检索条数
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块（system.Ads.AdMob）设计；2026-10-21 用户要求“limit 给更宽一些”，选定“只在带上级教训时加名额”，不整体调大默认条数。
必须保持的行为：
- MemoryIndex.search 传 ancestors 时，祖先只贡献教训（功能记录、规划不继承），分数乘 0.85^距离。
- 本模块教训照旧最多 limit 条（默认 5），不被祖先挤占；祖先另给 min(祖先候选数, max(search.inherit_max（默认 2，可设 0）, limit - 本模块条数)) 条，默认最多 5 + 2 = 7 条。
- 合并时两边各自保持同批降权后的次序，只按分数交错，不整体重排。
- 没有祖先（模块名只有两段）时结果与 v0.4 完全一样。
- 议题（entity）过滤只作用于本模块，祖先教训不受议题限制。
- 继承来的条目带 module 和 inherited: true，展示时标“上级 <模块>”；功能记录组只来自本模块。
入口：src/pmem/index/store.py 的 search 与 _merge_by_score；配置 search.inherit_max（core/config.py）。
