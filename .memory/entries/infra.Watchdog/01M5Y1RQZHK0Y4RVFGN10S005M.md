---
id: 01M5Y1RQZHK0Y4RVFGN10S005M
module: infra.Watchdog
entity: Testing
kind: correction
status: active
supersedes:
- 01M5A2P74CHG2PSTJX03ESYYKA
anchors:
- tests/test_watchdog.py
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 假子进程写完先读再 Popen，缓解 WinError 6 / 秒退偶发
verify: pytest tests/test_watchdog.py -q
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
更正：除 handshake 偶发外，test_code_update_reloads_idle_child 也曾报 WinError 6，疑似子进程未就绪。
处理：fixture 写完 child.py 后立刻 read_text 确认可读再启动 Watchdog。
仍成立：重负载并发时 handshake 偶发仍可能出现；机器空闲时稳定。不影响真实 pmem serve。
