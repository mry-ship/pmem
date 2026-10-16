---
id: 01M51S7PF17NJRGAAVR1TRXBT8
module: feature.Gate
entity: State
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/state.py#locked
- src/pmem/hooks/gate.py#handle
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 并发
- 竞态
- race condition
- 文件锁
- 误报未查
- 重复摘要
---
根因（已修复）：会话状态（sessions/<对话>.json）的读改写原先没有加锁。
Cursor 会并行执行同一批工具调用，每个调用的 Hook 是独立进程，各自读状态、改一项、整文件替换写回，后写的覆盖先写的（丢失更新）。
os.replace 原子替换只能保证文件不被写坏，保证不了更新不丢。

证据：2026-10-16 对话 9366e4ca 里并行 Grep 了 templates.py 和 hook_cmd.py，Onboarding、Gate 的 digest 相隔 14 毫秒先后记下，但 stop 仍判定 Onboarding 没查过而追问；
并行读 files.py、git.py（同属 Storage）时，同一模块的摘要附了两次，结束时 Storage 也被误追问。

修复：handle() 在调用事件处理之前，用 SessionState.locked() 对 sessions/<对话>.lock 加排他锁（Windows 用 msvcrt.locking，其他系统用 fcntl.flock），锁内重新读取状态，整个事件处理完再释放。
等锁最多 5 秒，超时就不加锁继续，宁可偶尔丢一次更新，也不卡住开发。
旧的 .lock 文件随会话文件一起 7 天后清理。

验证：线程并发单测；真实进程端到端测试，6 个 pmem hook post-tool 并行读不同模块，reviewed 里 6 个模块全部保留。

影响：同一对话的 Hook 变成串行，单个事件最多多等前一个事件的处理时间（通常不到 1 秒）。
