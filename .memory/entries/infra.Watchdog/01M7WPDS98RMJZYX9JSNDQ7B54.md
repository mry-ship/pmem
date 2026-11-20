---
id: 01M7WPDS98RMJZYX9JSNDQ7B54
module: infra.Watchdog
entity: Spawn
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/server/watchdog.py#_start
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 排除：只靠测试 sleep/read 扛 WinError 6
verify: 对照 src/pmem/server/watchdog.py#_start 含 winerror==6 重试
applies: 改 Watchdog 启动或 test_watchdog 稳定性时
---
排除：只在测试 fixture 里 sleep/read 来「解决」WinError 6，而不改 Watchdog._start。

原因：真实 pmem serve 同样走 _start；Popen 直接抛 OSError 时客户端会立刻收到无法启动。只改测试会让线上偶发仍暴露给 Cursor。
正确做法：_start 对 winerror==6 短重试，测试再作辅助加固。
