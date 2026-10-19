---
id: 01M5A1JBRA5SB1MWP4Y3Q7DS7A
module: infra.Common
entity: Layering
kind: decision
status: active
supersedes: []
anchors:
- tests/test_layering.py#test_packages_only_depend_downwards
- tests/test_layering.py#test_hook_process_stays_light
revision: git:501a142
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 分层
- 依赖方向
- 模块化
- 循环依赖
- layering
- architecture
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：包之间的依赖方向由 tests/test_layering.py 强制检查，规则写在 docs/architecture.md「分层」。
- 入口 cli 可以依赖任何包，其他包不能导入 cli。
- 汇总层 metrics（report、health）、bench 在最上；report、health 可以用 service。
- metrics.events 单独算最底层，只依赖 core，service、hooks、server 都可以写事件。所以按包看 service 与 metrics 互相引用，按文件看没有环。
- hooks 不能依赖 service；
  另有子进程测试确认导入 hook_cmd 和 gate 后没有加载 numpy、yaml、pmem.service、pmem.index.store。
  每次工具调用都起一个 Hook 进程，这些重依赖会让每次调用多等几百毫秒。
新增包或新依赖时先在 ALLOWED 里登记，否则测试失败。
同次修正文档：使用手册里 merge 未登记模块时“登记为别名”的旧描述、架构文档缺少的 importers 行、generate.integrations、events.lock、vectors.db 按需创建。
审计结果：落在 infra.Common 兔底的只有 main.py、brief.py、test_cli.py、test_layering.py 和空的 __init__.py；所有命令和子命令都在 README 或手册里。
