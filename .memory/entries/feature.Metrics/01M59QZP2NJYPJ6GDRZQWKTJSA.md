---
id: 01M59QZP2NJYPJ6GDRZQWKTJSA
module: feature.Metrics
entity: Events
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/events.py#log_event
- src/pmem/metrics/events.py#_exclusive
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 事件日志写坏
- 日志行截断
- 并发写入
- jsonl 损坏
- events.jsonl
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
结论：本机事件日志 events.jsonl 在 Windows 下会被多个 pmem 进程（CLI、Hook、MCP 服务）同时追加写坏行。
证据：本仓库日志第 2252 行只剩半截 JSON，前后三次 CLI 检索在同一秒内完成；
Windows 的追加写不是原子的（CRT 先定位到末尾再写），多个进程会互相覆盖。
新增用例 4 个进程各写 40 条大行，不加锁只剩 149/160 行。
处理：每次写入先取得同目录 events.lock 的独占锁（Windows 用 msvcrt.locking 锁第 0 字节，其他系统用 fcntl.flock），超过 20MB 的轮转也放进锁里，整行编码后一次写入。
锁放在单独文件而不是日志本身：Windows 字节锁是强制锁，锁日志会让同时读日志（report/health）的进程报错。
风险：拿不到锁时 msvcrt 重试约 10 秒后抛 OSError，该条事件被丢弃，不影响主流程；读取端仍会跳过坏行，旧日志里的坏行无需清理。
