---
id: 01M51R6108Z66X6CVCGJVREX3N
module: feature.Onboarding
entity: Hooks
kind: decision
status: active
supersedes:
- 01M51NZ5Q3M0H8WAPWJBRKDQ5F
anchors:
- src/pmem/cli/doctor_cmd.py
- src/pmem/generate/templates.py
revision: git:874e444
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- matcher
- 旧版Hooks
---
决定：pmem init 生成的 postToolUse Hook 的 matcher 从 "Read" 扩为 "Read|Grep|Glob|SemanticSearch|codebase_search"，Claude Code 的 PostToolUse 也加上 Grep、Glob，让搜索代码时也能附记忆摘要。

已接入的老项目需要重新运行一次 pmem init。它只替换以“pmem hook”开头的 Hook 条目，不覆盖已有的 config.yaml 和 modules.yaml。pmem doctor 发现 pmem 的 postToolUse 条目 matcher 不含 Grep 时，提示“Hooks 是旧版…请重新运行 pmem init 更新”。没更新的项目也不会完全漏掉：回合结束时会从对话记录补查本轮看过的代码。
