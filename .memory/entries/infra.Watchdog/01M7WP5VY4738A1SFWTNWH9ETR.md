---
id: 01M7WP5VY4738A1SFWTNWH9ETR
module: infra.Watchdog
entity: Testing
kind: correction
status: active
supersedes:
- 01M5Y1RQZHK0Y4RVFGN10S005M
anchors:
- src/pmem/server/watchdog.py#_start
- tests/test_watchdog.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: WinError 6：_start 短重试 + 测试握手重试
verify: pytest tests/test_watchdog.py -q 连跑多次无失败
applies: Windows；Watchdog 拉起子进程或跑 test_watchdog
---
更正：仅靠 fixture「写完 child.py 再 read_text」仍不够——重负载下 handshake / hung_request 等仍会偶发 WinError 6（Popen 直接抛 OSError），真实 pmem serve 同样走 Watchdog._start。

现行处理：
1) Watchdog._start 对 winerror==6 最多短重试 3 次（间隔 50/100ms），仍失败再进崩溃退避；
2) 测试 fixture 在 read_text 后再 sleep 50ms；handshake 若收到「无法启动/WinError 6」可短重试换新请求 id。

仍成立：机器极忙时仍可能偶发，但应远少于只靠读文件确认的方案。
