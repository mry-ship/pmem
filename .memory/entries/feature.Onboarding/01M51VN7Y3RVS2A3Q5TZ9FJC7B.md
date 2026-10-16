---
id: 01M51VN7Y3RVS2A3Q5TZ9FJC7B
module: feature.Onboarding
entity: Hooks
kind: decision
status: active
supersedes:
- 01M51R6108Z66X6CVCGJVREX3N
anchors:
- src/pmem/cli/init_cmd.py#merge_hooks
- src/pmem/cli/doctor_cmd.py
- src/pmem/generate/templates.py
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- matcher
- 旧版Hooks
- beforeMCPExecution
---
决定：pmem init 生成的 Cursor Hooks 中，postToolUse 的 matcher 为 "Read|Grep|Glob|SemanticSearch|codebase_search|Shell"：读代码、搜索代码时附记忆摘要，终端命令执行后核对它实际改了哪些文件。
Claude Code 的 PostToolUse 加上 Grep、Glob、Bash，Codex 的 PostToolUse 加上 Bash。
不再生成 beforeMCPExecution（检索改为返回结果后才登记，before-mcp 只为兼容旧配置保留，直接放行）。

升级：老项目重新运行一次 pmem init。
它只替换以“pmem hook”开头的条目，并会删掉模板里已经没有的事件下的 pmem 条目（如旧的 beforeMCPExecution），不覆盖 config.yaml、modules.yaml 和其他工具自己的 Hook。
pmem doctor 发现 postToolUse 的 matcher 不含 Grep 或 Shell 时，提示“Hooks 是旧版…请重新运行 pmem init 更新”。

没更新的项目也能用：回合结束时会从对话记录补查本轮看过的代码，只是没有终端命令的事后核对。
