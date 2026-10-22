---
id: 01M5HE5DT5KHRFK2G3TRP27QMG
module: feature.ModuleCatalog
entity: AutoSync
kind: feature
status: active
supersedes:
- 01M5HE0A9Z8MDCBXMVRCHG5MZV
anchors:
- src/pmem/catalog/autosync.py
- src/pmem/core/autosync.py
- src/pmem/cli/sync_cmd.py
- tests/test_autosync.py
revision: git:be996bf
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 自动发现没登记的代码目录：后台 pmem sync --auto，默认自动追加登记并写明新增数量
applies: 项目已有 .memory/modules.yaml 且 sync.auto 不是 off
aliases:
- 自动登记
- 自动同步
- 新模块
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-22）要求新增模块不靠人记得跑 pmem sync/health；默认自动追加登记；执行了就要写明新增多少个模块。
必须保持：
- sync.auto：apply（默认）/ remind / off；interval_minutes 30，full_hours 24。
- 触发：改到没归属模块的代码文件时立即（20 秒内一次）；sessionStart 按间隔；都在后台进程。
- 后台：加锁；目录指纹没变就结束；快速扫描不读历史，full_hours 做完整扫描。apply 只追加；正文有注释时退回提醒。
- 数量必须写明：提醒文字写“共新增 N 个模块、M 个冷候选…”并要 Agent 在回复里写明数量；
  命令行输出同样带数量；
  事件 autosync 记各类计数；
  每次自动登记在 autosync.json 的 history 留一条（最近 20 次，含模块名），pmem sync --history 查看。
- 结果下一次 post-tool 告诉 Agent 一次；PMEM_NO_AUTOSYNC 关闭拉起（测试默认设）。
入口：pmem sync --auto edit|session|full、pmem sync --history；触发、计数和提醒文字在 core/autosync.py。
