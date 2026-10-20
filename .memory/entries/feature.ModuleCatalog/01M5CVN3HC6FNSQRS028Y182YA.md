---
id: 01M5CVN3HC6FNSQRS028Y182YA
module: feature.ModuleCatalog
entity: Split
kind: feature
status: active
supersedes:
- 01M5CQ6ENSTB62W93Q81F27WTS
anchors:
- src/pmem/catalog/migrate.py#plan_split
- src/pmem/catalog/migrate.py#_follow_supersedes
- src/pmem/catalog/yamlfile.py#ModulesFile.read
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: split 时被替代记忆跟随替代者且预览如实；sync 不往废弃模块挂变体；modules.yaml 写坏报行号
verify: uv run pytest tests/test_migrate_split.py tests/test_sync.py tests/test_robustness.py
  -k "superseded or deprecated or catalog_reader"
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺、两轮复查后全部修复。
必须保持：
1) migrate split：被替代的记忆跟着替代它的记忆走（--assign 指定的不动，几条替代者分到不同模块时留在原模块并列出）；跟着搬走的不再出现在“横跨多个模块、留在原模块”的预览里。
2) sync 不把新的变体目录追加到已废弃的模块。
3) sync、migrate 读 modules.yaml 时 YAML 写坏、顶层不是键值对报 RegistryError（行号按整个文件算，含保留的注释块），不再打异常栈。
4) migrate move 遇到读不出的记忆文件报 MigrateError。
入口：catalog/migrate.py plan_split / _follow_supersedes / plan_move、catalog/yamlfile.py ModulesFile.read、catalog/sync.py。
