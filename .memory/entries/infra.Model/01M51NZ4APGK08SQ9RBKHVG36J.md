---
id: 01M51NZ4APGK08SQ9RBKHVG36J
module: infra.Model
entity: ReviewDefaults
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
revision: git:6d89f59
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- read_digest
- question_review
- 默认开关
---
决定：记忆审查的两个开关 gate.read_digest（读代码时附摘要）和 gate.question_review（结束时要求核对问题涉及的模块）默认都开。

原因：已接入的项目升级 pmem 后，config.yaml 里没有这两个键，读取时按 Config 的默认值合并，所以升级后直接生效，不用改配置。gate.mode 为 off 时两者都不触发。

风险：读代码时的摘要依赖 postToolUse Hook。
老项目必须重新运行 pmem init，或者手工在 hooks.json 里加 "pmem hook post-tool"（matcher: Read），否则只有结束时的核对生效。
pmem doctor 会对此给出警告。
