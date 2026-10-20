---
id: 01M5CFJFP3T9HDEAH4SZGX78B9
module: infra.Model
entity: ReviewDefaults
kind: decision
status: active
supersedes:
- 01M51NZ4APGK08SQ9RBKHVG36J
anchors:
- src/pmem/core/config.py#DEFAULTS
- src/pmem/generate/templates.py#CURSOR_HOOKS
- src/pmem/hooks/gate.py#_reviews_on
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: read_digest 与 question_review 默认开；读码摘要依赖完整的 postToolUse matcher
aliases:
- read_digest
- question_review
- 默认开关
---
决定：记忆审查的两个开关 gate.read_digest（读代码时附摘要）和 gate.question_review（结束时要求核对问题涉及的模块）默认都开。
原因：已接入的项目升级 pmem 后 config.yaml 里没有这两个键，读取时按默认值合并，升级后直接生效。gate.mode 为 off 时两者都不触发。
风险：读代码时的摘要依赖 postToolUse Hook，老项目要重新运行 pmem init。
更正旧记忆的手工办法：只在 hooks.json 加 matcher "Read" 已不够，现行 matcher 是 Read|Grep|Glob|SemanticSearch|codebase_search|Shell，缺 Grep 或 Shell 时 doctor 判为“Hooks 是旧版”，搜索时不附摘要、终端命令不做事后核对。
没接 postToolUse 时只有结束时的核对生效。
