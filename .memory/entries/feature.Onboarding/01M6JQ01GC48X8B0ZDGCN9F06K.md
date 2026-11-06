---
id: 01M6JQ01GC48X8B0ZDGCN9F06K
module: feature.Onboarding
entity: Hooks
kind: correction
status: active
supersedes:
- 01M51VN7Y3RVS2A3Q5TZ9FJC7B
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_QUIET
revision: git:f034aa1
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: quiet 须保留 Shell 版 postToolUse
verify: CURSOR_HOOKS_QUIET 含 postToolUse matcher Shell；无 Read
applies: Cursor Hooks；Windows quiet
verified: '2026-11-06'
verified_at: '2026-11-06T14:52:03.318+08:00'
---
更正：Windows quiet 不是「完全没有 postToolUse」。
必须保留 matcher=Shell 的 postToolUse，否则终端 pmem search 无法在执行后登记「已查过」，MCP 不可用时闸门会一直拦改代码。
去掉的是 Read|Grep|Glob|语义搜索 与 afterFileEdit/preCompact。
