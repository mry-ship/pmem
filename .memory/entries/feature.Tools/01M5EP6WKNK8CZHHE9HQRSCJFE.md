---
id: 01M5EP6WKNK8CZHHE9HQRSCJFE
module: feature.Tools
entity: Hierarchy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#_children_rows
- src/pmem/service/search.py#_related
- src/pmem/service/record.py#_sibling_lessons
- src/pmem/server/app.py#build_server
- src/pmem/cli/brief.py#_children_lines
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 查父模块附各下级最新 5 条记忆标题（含功能记录）；related 双向；只能替代本模块或下级
verify: uv run pytest tests/test_module_hierarchy.py -k "children or related or supersede
  or sibling"
aliases:
- 下级模块
- 子模块要点
- 手工关联
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块设计。
用户用法：大模块（system.Ads）记公共逻辑，各 SDK 子模块记详细变化；
问整个广告系统时先定位父模块再看各子模块。
用户（2026-10-21）明确要求往下不能放松、要精准：每个下级最多 5 条，功能记录也要列（最初只给 2 条教训被否定）。
必须保持的行为：
- search_memory 响应带 children：每个登记的下级给 count、再下一级个数 children，以及 latest：该下级及其更下级最新 5 条现行记忆（教训和功能记录/规划都算，按日期倒序）的 id、类型、议题、日期、标题，来自更下级的带 module；
  只给标题不给全文；
  带 as_of 时按那天的现行记忆算。
  memory_graph 同样带 children。
- inherited_hint：问整体情况先看 latest，涉及某个下级的细节再按它检索（直接查下级时仍是完整结果：教训全文 + 功能记录标题 + 上级教训）。
- related：先列手工登记的 related（双向），再接计算出的，直系不算相关。memory_graph 带 lineage；list_modules 每行带 parent、children。
- supersedes 只允许本模块和下级模块的记忆（见 SupersedeLineage）。兄弟有同议题教训时返回 sibling_similar 提示写到父模块。
- --brief 把 latest 渲染成“  <下级> ▸ 类型｜议题｜日期｜id：标题”。
入口：src/pmem/service/search.py（_children_rows、_related）、service/record.py、server/app.py、cli/brief.py。
