---
id: 01M5A2P74CHG2PSTJX03ESYYKA
module: infra.Watchdog
entity: Testing
kind: risk
status: active
supersedes: []
anchors:
- tests/test_watchdog.py#dog
- src/pmem/server/watchdog.py#_from_client
revision: git:abef6dc
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 偶发失败
- flaky
- 测试不稳定
- 握手失败
- 看门狗测试
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
风险：tests/test_watchdog.py 在全量测试中偶发失败。
2026-10-19 共 3 次，分别是 test_hung_request_times_out_and_restarts、test_crash_restarts_child_and_replays_handshake 等不同用例，都挂在 fixture 的 handshake()：客户端发 initialize 收到的是 error 而不是 result。
从代码看，看门狗只在收到 initialize 时子进程已退出（self.child is None）才会回错误；假子进程对 initialize 不会回错。所以假子进程是刚启动就退出了，或 Popen 启动失败。
未证实的猜测：Windows 上 fixture 刚写好 child.py 就启动，杀毒软件扫描新文件时可能锁住它。
证据：3 次失败都发生在同时跑 pmem doctor（预热语义模型）等重任务时；机器空闲时连续 3 轮全量测试和单独重跑都通过。
处理：再出现时看断言消息里的 (reply, restarts)。
若 error 是“意外退出（返回码 N）”或“无法启动”，就在 fixture 里写完脚本后先试读一次再启动，或改用 python -c 内联假子进程。
不影响真实的 pmem serve。
