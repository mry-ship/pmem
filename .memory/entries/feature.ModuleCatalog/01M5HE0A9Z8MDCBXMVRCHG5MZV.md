---
id: 01M5HE0A9Z8MDCBXMVRCHG5MZV
module: feature.ModuleCatalog
entity: AutoSync
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/catalog/autosync.py
- src/pmem/core/autosync.py
- src/pmem/cli/sync_cmd.py
- tests/test_autosync.py
revision: git:8d3a154
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 自动发现没登记的代码目录：后台 pmem sync --auto，默认自动追加登记
applies: 项目已有 .memory/modules.yaml 且 sync.auto 不是 off
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-22）要求新增模块不靠人记得跑 pmem sync/health，迭代快的项目半天就加很多目录；选定“自动追加登记”为默认。
必须保持：
- config.yaml 的 sync.auto：apply（默认）/ remind / off；interval_minutes 默认 30（会话开始的节流），full_hours 默认 24。
- 触发：Agent 改到没归属任何模块的代码文件时立即（20 秒内只拉一次）；sessionStart 距上次超过间隔时。均拉起后台进程，不阻塞。
- 后台（catalog/autosync.py run_auto）：加锁，先比目录指纹（含代码文件的目录集合 + modules.yaml 修改时间），没变就结束；
  快速扫描不读提交历史、不统计记忆；
  超过 full_hours 做完整扫描（热度 + 记忆转正）。
- apply 走 apply_plan 只追加；modules.yaml 正文有注释时不写、退回提醒（重写会丢注释）。
- 结果存本机缓存 autosync.json，下一次 post-tool 告诉 Agent 一次，由它转告用户。
- 环境变量 PMEM_NO_AUTOSYNC 关闭拉起；测试 conftest 默认设了。
入口：pmem sync --auto edit|session|full；触发与提醒文字在 core/autosync.py。
