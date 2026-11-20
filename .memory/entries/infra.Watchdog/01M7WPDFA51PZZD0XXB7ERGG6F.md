---
id: 01M7WPDFA51PZZD0XXB7ERGG6F
module: infra.Watchdog
entity: Spawn
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/server/watchdog.py#_start
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 子进程 WinError 6 短重试并打日志
verify: pytest tests/test_watchdog.py -q 连跑多次无失败
applies: Windows；Watchdog 拉起子进程或跑 test_watchdog
aliases:
- WinError 6
- 句柄无效
- 启动重试
---
需求来源：深度稳定复核时全量 pytest 偶发 WinError 6；真实 pmem serve 与测试共用 Watchdog._start，不能只在测试里绕过；再补重试可观测性，避免掩盖根因。

必须保持：
1) 拉起 MCP 子进程时，若 Windows 上 Popen 抛 winerror==6（句柄无效），在进崩溃退避前最多短重试 3 次（间隔约 50ms、100ms）。
2) 每次重试与重试后成功须写看门狗日志（stderr），提示若反复出现应查句柄/权限。
3) 非 WinError 6 或重试仍失败：行为与原先一致——记无法启动并调度重启。
4) 测试：假子进程写盘后先读再短等；handshake 收到「无法启动/WinError 6」时可换请求 id 短重试（见同模块 Testing 更正）。

入口：src/pmem/server/watchdog.py（_start）；tests/test_watchdog.py；pmem serve。
