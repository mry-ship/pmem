---
id: 01M5HFCN4M35XGSXA6K6GH59SR
module: feature.ModuleCatalog
entity: AutoSync
kind: feature
status: active
supersedes:
- 01M5HE5DT5KHRFK2G3TRP27QMG
anchors:
- src/pmem/catalog/autosync.py
- src/pmem/core/autosync.py
- src/pmem/cli/sync_cmd.py
- tests/test_autosync.py
revision: git:ed5144a
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 自动发现没登记的代码目录：后台 pmem sync --auto，默认自动追加登记并写明新增数量
applies: 项目已有 .memory/modules.yaml 且 sync.auto 不是 off
aliases:
- 自动登记
- 自动同步
- 新模块
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:23.529+08:00'
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-22）要求新增模块不靠人记得跑 pmem sync/health；默认自动追加登记；执行了就要写明新增多少个模块。
必须保持：
- sync.auto：apply（默认）/ remind / off；interval_minutes 30，full_hours 24。
- 触发：改到没归属模块的代码文件时立即（20 秒内一次），但上次扫描后仍没归属的目录（unresolved_dirs：散落文件、只提醒没登记的）不再触发，免得每改一次白遍历全项目；sessionStart 按间隔；都在后台进程。
- 后台：加锁；目录指纹没变就结束；快速扫描不读历史，full_hours 做完整扫描。apply 只追加；正文有注释时退回提醒。
- 数量必须写明：提醒写“共新增 N 个模块、M 个冷候选…”并要 Agent 在回复里写明；
  命令行输出、事件 autosync 带计数；
  autosync.json 的 history 留最近 20 次，pmem sync --history 查看。
- 提醒在下一次 post-tool 给一次；后台正在扫（锁在）时不读改写状态，免得覆盖刚写的结果和历史。PMEM_NO_AUTOSYNC 关闭拉起（测试默认设）。
端到端实测：pmem hook edited 0.25 秒返回，1.6 秒后登记完成。入口：pmem sync --auto edit|session|full、--history；触发与提醒在 core/autosync.py。
