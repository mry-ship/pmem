---
id: 01M52HRGFVNCSBJHK8EKR8ZYB9
module: feature.ModuleCatalog
entity: Deprecate
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/catalog/migrate.py#plan_deprecate
- src/pmem/core/registry.py#deprecated
- src/pmem/service/record.py#_record
- src/pmem/hooks/reminders.py#_deprecated
- src/pmem/cli/seed_cmd.py#seed_plan
- src/pmem/metrics/health.py#build_health
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 废弃模块
- 下线
- 只读
- deprecated
- deprecate
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：模块废弃用 modules.yaml 里的 status: deprecated 表示（Module.deprecated），由 pmem migrate deprecate <模块> [--undo] 写入，默认预览、--apply 执行；只接受登记模块的正式名，重复废弃或撤销未废弃的模块会拒绝。

废弃后：旧记忆照常可查；写入（含草稿覆盖）被拒绝并提示撤销命令；list_modules 的行带 deprecated: true；闸门结束提醒不再要求为它写记忆（否则 Agent 会收到“去写”的提醒、写入又被拒）；pmem seed --plan 和健康报告的“没人检索的模块”都跳过它。路径仍归该模块，改这些代码前闸门照样要求先查记忆。

原因：业务下线后旧结论仍有参考价值（排查历史数据、复用方案），但不该再积累新记忆；归档整个模块会让这些结论查不到。

风险：废弃模块的代码如果还在改，新结论写不进去，需要先 --undo；未登记模块不能废弃。
