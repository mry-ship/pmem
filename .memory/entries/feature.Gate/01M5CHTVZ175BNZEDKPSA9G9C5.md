---
id: 01M5CHTVZ175BNZEDKPSA9G9C5
module: feature.Gate
entity: GateSplit
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#Gate
- src/pmem/hooks/gate.py#handle
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: gate.py 按职责拆成 6 个混入类，Gate 只留事件分发；常量要在定义它的文件里替换
verify: uv run pytest tests/hooks tests/test_layering.py
aliases:
- 拆分 gate
- 混入类
- mixin
- 闸门结构
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
取舍：原 gate.py 约 1100 行、一个类混 8 类职责。
各部分共用会话状态、配置和记忆缓存，拆成独立对象要大量传参、改方法体；
选了混入类：MemoryView（memories.py）、Review、Guard、McpCalls（mcp.py）、Snapshots、Reminders，Gate 继承它们，只留 __init__、各 on_* 事件、HANDLERS、handle。
方法体逐字搬迁（按 AST 比对过），只把跨文件用到的 _command_key、_needs_snapshot、_GLOB 改成不带下划线的公开名。
代价与约束：
- 混入类之间靠 self 互相调用（如 Guard 用 MemoryView 的 memory_count），单独实例化没意义，只通过 Gate 用。
- 测试用 monkeypatch 改模块常量时要改定义它的文件（如 SLOW_SNAPSHOT_SECONDS 在 pmem.hooks.snapshot），改 pmem.hooks.gate 里的同名属性不生效。
  替换方法仍可以直接 patch Gate.xxx。
- cli_args、may_change_unseen、shell_write_targets 仍从 gate 重新导出，旧的 import 路径不变。
- 拆分只用原有的导入，没有给 Hook 进程加重型依赖。
