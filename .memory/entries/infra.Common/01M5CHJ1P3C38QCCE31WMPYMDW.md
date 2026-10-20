---
id: 01M5CHJ1P3C38QCCE31WMPYMDW
module: infra.Common
entity: CLI
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem search 不写 --limit 时按 config.yaml 的 search.limit
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户 2026-10-20 要求修复 search.limit 配置不生效。
必须保持：命令行 pmem search 的 --limit 默认不设值，由服务层按 search.limit（默认 5）取；
写了 --limit 就用给定值。
不要再把默认值写死成 5，否则配置永远不生效。
入口：cli/main.py 的 search 子命令。
