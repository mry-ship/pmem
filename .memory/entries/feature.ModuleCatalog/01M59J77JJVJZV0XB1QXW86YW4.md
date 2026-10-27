---
id: 01M59J77JJVJZV0XB1QXW86YW4
module: feature.ModuleCatalog
entity: Layering
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/catalog/sync.py#plan_sync
- src/pmem/catalog/sync.py#apply_plan
- src/pmem/catalog/yamlfile.py#ModulesFile
- src/pmem/catalog/migrate.py#plan_move
- src/pmem/core/registry.py#from_dict
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 分层
- 目录同步
- 废弃模块被覆盖
- modules.yaml 校验
- catalog
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:14.279+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：modules.yaml 的维护逻辑独立成 src/pmem/catalog 包，不依赖 cli：yamlfile（读写，保留文件头注释、读入时统一成 LF、引号里的 " #" 不算注释）、migrate（rename/merge/split/deprecate/move 规划与记忆搬家）、sync（规划）、coverage（覆盖率）。
cli/migrate_cmd.py、sync_cmd.py 只解析参数、渲染、确认 --apply；
metrics/health、doctor、import 直接用 catalog。
原因：原先 health 反向导入 cli，import 自己用 yaml.safe_dump 写文件丢文件头、写成 CRLF。
同时修复：
1) sync 新目录与已废弃模块同名时，原来 apply_plan 用 modules.update 整段覆盖废弃模块（丢 status、别名、路径）；现在列入 conflicts 不自动登记，apply 对已有键一律不覆盖。
2) 没有版本库或取不到提交历史时（history=False）不按热度分新模块/冷候选，也不提示闲置模块。
3) ModuleRegistry 校验：paths/aliases 写成字符串时包成列表（原来按字符拆开），模块名不带大类、内容不是键值对时报 RegistryError（原来 IndexError 让所有工具报错）。
新增 pmem migrate move <id>... --to <模块>，把归错模块的记忆按 id 搬走。
