---
id: 01M72R0YGB3EQV586TA19Z8YGH
module: infra.Common
entity: ContextCmd
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/context_cmd.py#run_context
- tests/test_layering.py
revision: git:dbfdab4
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: pmem context 命令与文档清单已同步
verify: uv run pytest tests/test_layering.py tests/test_context.py
---
需求：终端调试与后台刷新入口。必须保持的行为：
- pmem context [--refresh] [path] [--json]；--refresh 重算常一起改缓存。
- 分层：context 包只依赖 core/vcs；hooks 与 service 可依赖 context。
- 加命令时同步 README 命令速查、docs/pmem-guide.html（命令表、配置 harness、report 指标）、docs/architecture.md（context 包与分层）、设计文档第 11 节日常维护表。
入口：cli/context_cmd.py、cli/main.py；tests/test_layering.py 登记 context 层。
