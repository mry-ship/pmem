---
id: 01M5EP7DV0EDP13VXRBFECMY5B
module: feature.Metrics
entity: Hierarchy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#_hierarchy_issues
- src/pmem/metrics/health.py#_duplicate_modules
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: health 新增“父子模块结构”一节；父子、不同分支下同名末段不再报疑似重复
verify: uv run pytest tests/test_module_hierarchy.py -k health
aliases:
- 健康报告父子模块
- 疑似重复模块
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块设计。之前健康报告把 system.AdMob 与 system.Ads 这类报成疑似重复，用户问父子模块怎么划分。
必须保持的行为：
- 疑似重复模块：去掉大类后名字完全相同（跨大类）照报；名字相近时，直系或不同父模块下的子模块（AdMob.Android 与 Max.Android）不报。
- “父子模块结构”一节（health 的 hierarchy 键）列出：超过 4 段、父模块未登记、旧 parent 字段（给出 migrate rename 命令）、related 指向未登记模块、只有一个下级且自己没有路径和记忆的父模块、兄弟模块有同议题教训（建议写到父模块并 supersedes）。
- 跨模块替代检查不把“替代下级模块的记忆”算异常。
入口：src/pmem/metrics/health.py（_duplicate_modules、_hierarchy_issues、_cross_module_supersedes）。
