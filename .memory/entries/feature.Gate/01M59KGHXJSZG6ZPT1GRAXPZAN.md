---
id: 01M59KGHXJSZG6ZPT1GRAXPZAN
module: feature.Gate
entity: GateDefaults
kind: correction
status: active
supersedes:
- 01M51VMYMTTEC3T8HFRCX3ZTDW
anchors:
- src/pmem/hooks/gate.py#_note_cli_calls
- src/pmem/hooks/gate.py#_confirm_cli_searches
- src/pmem/hooks/gate.py#error_notice
- src/pmem/hooks/shell.py#cli_args
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 终端检索
- pmem search 算查过
- 闸门出错
- hook-errors
- 放行提示
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正（2026-10-19）：终端 pmem search/graph --module 原先在执行前就登记“已查过”，命令失败、根本没跑（写在 || 之后）也算，Agent 并没看到记忆。现在：
- preToolUse 只记为待确认（会话状态 cli_pending，按命令键存）；同一条命令里先查再写仍放行查过的模块。
- postToolUse 拿到输出后，输出里出现该模块名（不分大小写）才登记；
  看不到记 search_call_unseen 事件。
  Cursor 的 Shell postToolUse 带 tool_output（实测），Claude Code、Codex 带 tool_response；
  拿不到输出时按执行完算。
- 写在 || 之后的不算；输出被丢弃（> $null、| Out-Null、重定向到文件）仍不算。

新增：Hook 出异常时照旧放行并写 hook-errors.log，但原先用户完全看不到、以为检查生效了。
现在下一次 post-tool 的 additional_context 或 stop 的 followup 里附一句，要 Agent 提醒用户运行 pmem doctor；
用 hook-errors.seen 标记，同一批错误只提醒一次，没标记时只看近 24 小时，gate.mode: off 不提醒。

仍然有效的默认值：gate.mode 默认 block、analysis_reminder 默认开；MCP 检索在 afterMCPExecution 返回 ok:true 后才登记；只算现行记忆；查了哪个模块只放行哪个。

风险：改代码途中 Hook 自身出错（如编辑一半的 NameError）也会被提醒，属预期。
