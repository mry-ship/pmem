---
id: 01M5Y1RH6NXFXFAP8DFC769KFA
module: infra.Model
entity: Schema
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/schema.py
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: v0.7 开工：core/schema.py 提供 SchemaError 与 expect_* 基础校验
verify: pytest tests/core/test_schema.py
applies: 实现或接入 v0.7 边界校验时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：用户要求再开 v0.7 类型安全。
必须保持：schema 只用标准库；SchemaError 带 path；expect_mapping/list/str/bool/number/one_of 行为稳定；list 允许单字符串升为一项。
尚未接入 config/modules/entry/Hook（下一阶段迁移）。
适用：写或调用边界校验时。
入口：src/pmem/core/schema.py；测试 tests/core/test_schema.py。
