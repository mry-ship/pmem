---
id: 01M52HVNEMW34BD1RXZM9WNVR8
module: feature.Gate
entity: StopReminder
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_deprecated
- src/pmem/hooks/gate.py#_pending_nudges
- src/pmem/hooks/gate.py#_consulted_only
revision: git:5003560
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 结束提醒
- 废弃模块
- stop
---
决定：结束提醒（改了代码没写记忆、只查了记忆没写结论）跳过已废弃的模块（modules.yaml 里 status: deprecated）。
原因：废弃模块拒绝新写入，提醒 Agent 去写只会换来一次失败的写入和一轮无意义的续跑。
改前拦截照旧：废弃模块的路径仍归它，改代码前还是要先查它的旧记忆。
风险：废弃后如果还在大改这块代码，新结论不会被提醒记录，需要先 pmem migrate deprecate <模块> --undo --apply。
