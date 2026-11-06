---
id: 01M6QWV3YW4GF91NV7RW2HYB81
module: infra.Model
entity: Schema
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/schema.py
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: core/schema.py 路径挂到 infra.Model
verify: module_for_path('src/pmem/core/schema.py')→infra.Model；resolve_module('Schema')→infra.Model
applies: 改 v0.7 边界校验时
---
需求来源：边界校验属于数据模型/配置校验，不应只靠 Common 兜底。
必须保持：改 schema.py 或 test_schema 时按 infra.Model 查记忆；短名 Schema 可解析到本模块。
入口：modules.yaml infra.Model.paths / aliases。
