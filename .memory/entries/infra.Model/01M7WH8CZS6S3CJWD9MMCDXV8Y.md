---
id: 01M7WH8CZS6S3CJWD9MMCDXV8Y
module: infra.Model
entity: Schema
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 边界校验：未知键警告、报错带字段路径、Hook 软校验
verify: uv run pytest tests/core/test_schema.py tests/core/test_config.py
applies: 实现或改 v0.7 边界校验时
---
需求来源：v0.7 设计稿 §3.4。

必须保持：
- schema 提供 SchemaError、expect_*、suggest_key、unknown_key_warnings；只用标准库。
- Config.load / ModuleRegistry 对未知键只警告（带相近键提示），不拒绝；facets 超过 4 个维度警告。
- 配置类型错误报错带 .memory/config.yaml：字段路径。
- Entry 头类型错误带路径；when 非对象报错；未知字段仍进 extra。
- Hook：validate_hook_payload 只警告；hook_cmd 记入 hook-errors.log 并放行。
- pmem doctor 汇总 config/modules 的警告。

入口：src/pmem/core/schema.py、config.py、registry.py、entry.py；hooks/payload.py；cli/hook_cmd.py、doctor_cmd.py。
