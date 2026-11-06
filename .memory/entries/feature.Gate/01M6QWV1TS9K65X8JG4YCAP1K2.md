---
id: 01M6QWV1TS9K65X8JG4YCAP1K2
module: feature.Gate
entity: SeenHandoff
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/seen.py
- .memory/modules.yaml
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: core/seen.py 路径挂到 feature.Gate
verify: module_for_path('src/pmem/core/seen.py')→feature.Gate
applies: 改对话去重或 CLI 交接时
---
需求来源：对话去重与 CLI 交接实现在 core/seen.py，原先只靠 Common 兜底。
必须保持：改 seen.py 时闸门/检索按 feature.Gate 查记忆；议题 SeenHandoff 仍可用。
入口：.memory/modules.yaml feature.Gate.paths。
