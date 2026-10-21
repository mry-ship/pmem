---
id: 01M5EP6VWJVM5EBMDCEYAPS3VP
module: feature.Retrieval
entity: Inherit
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#search
- src/pmem/core/config.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 查子模块带上各级上级的教训（默认 2 条，自身不足时补满），不继承功能记录
verify: uv run pytest tests/test_module_hierarchy.py -k "inherit or capped"
aliases:
- 上级教训
- 祖先继承
- 父模块的坑
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块（system.Ads.AdMob）设计，用户确认“祖先教训最多占 2 个名额，本模块教训不够时多给”。
必须保持的行为：
- MemoryIndex.search 传 ancestors 时，祖先只贡献教训（功能记录、规划不继承），分数乘 0.85^距离。
- 名额：min(祖先候选数, max(search.inherit_max（默认 2，可设 0 关闭）, limit - 本模块已选条数))，合并后按分数排序。
- 议题（entity）过滤只作用于本模块，祖先教训不受议题限制。
- 继承来的条目带 module 和 inherited: true，展示时标“上级 <模块>”。
- 功能记录组只来自本模块。
入口：src/pmem/index/store.py 的 search；配置 search.inherit_max（core/config.py）。
