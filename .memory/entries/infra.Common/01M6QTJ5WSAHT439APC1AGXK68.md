---
id: 01M6QTJ5WSAHT439APC1AGXK68
module: infra.Common
entity: LocalCache
kind: feature
status: active
supersedes:
- 01M6P1AAZ8FEY1HT052JJVW3N0
anchors:
- .gitignore
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: gitignore 忽略 .memory/cache
verify: git check-ignore -v .memory/cache/health-latest.json
applies: 仓库根目录纳入版本控制时
---
根目录 .gitignore 增加 .memory/cache/，避免本机 health 报告被误提交。
仍提交 .memory/entries 与 modules；wiki 与 cache 均忽略。
