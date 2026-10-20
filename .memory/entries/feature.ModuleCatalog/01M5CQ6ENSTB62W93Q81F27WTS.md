---
id: 01M5CQ6ENSTB62W93Q81F27WTS
module: feature.ModuleCatalog
entity: Split
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/catalog/migrate.py#_follow_supersedes
- src/pmem/catalog/sync.py#_variant_owner
- src/pmem/catalog/yamlfile.py#dump_modules
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: split 时被替代记忆跟随替代它的记忆；sync 不往废弃模块挂变体目录
verify: uv run pytest tests/test_migrate_split.py tests/test_sync.py tests/test_integrations.py
  -k "superseded or deprecated or comment_only"
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，审查复现出三处问题后修复。
必须保持：
1. pmem migrate split 分配记忆时，被替代的记忆跟着替代它的记忆去同一模块（替代链会一路跟过去），不能产生写入时会被拒绝的跨模块替代；--assign 指定的不动；被分到不同模块的几条同时替代的留在原模块并列入未定去向。
2. pmem sync 判断“新目录是已有模块的又一个变体”时跳过已废弃模块，废弃模块只读、不再挂新路径。
3. modules.yaml 只有注释且末行没换行时，重写后正文不能接在注释行后面变成注释。
入口：catalog/migrate.py 的 plan_split（_follow_supersedes）、catalog/sync.py 的 _variant_owner、catalog/yamlfile.py 的 dump_modules。
