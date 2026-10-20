---
id: 01M5A0PDW81SDRHCD9T7HC0E8Z
module: feature.Gate
entity: State
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#handle
- src/pmem/hooks/memories.py#fill_stale
- src/pmem/hooks/memories.py#memory_lines
revision: git:4e8ab24
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 锁等待
- Hook 排队
- 需核实
- stale
- 并发 hook 慢
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：会话锁内不再核对“需核实”。
handle() 持锁执行事件处理时，摘要和拦截提示里的需核实标记、页脚提示先写成占位符（\x00stale:<id>\x00、\x00footer:<ids>\x00），释放锁后 fill_stale 统一调用一次 stale_problems 再填回；
本段没有需核实记忆时页脚连同换行去掉。
原因：核对要查版本库历史，本仓库每个模块首次 0.3～0.5 秒，一次事件可能给多个模块出摘要，原先全在锁内，同一对话并行的 Hook 只能排队（issue #11）。读记忆文件仍在锁内（缓存后很快）。
证据：单测在 stale_problems 里尝试另开句柄加锁，能拿到即说明已释放；全量 521 个测试通过。
影响：只经 handle() 且有对话 id 时延后；直接调用 Gate 方法（单测）、没有对话 id 时照旧当场核对。
风险：以后新增返回内容的路径若把摘要文字存进会话状态或日志，会带出占位符，需在 fill_stale 之后再存。
