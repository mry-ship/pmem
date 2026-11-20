---
id: 01M7WKD84GBC8HDPNGRJTCEJ67
module: infra.Model
entity: Schema
kind: feature
status: active
supersedes:
- 01M7WH8CZS6S3CJWD9MMCDXV8Y
anchors:
- src/pmem/cli/doctor_cmd.py#_check_when_facets
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 边界校验：未知键路径提示、空 facets、Hook 软校验、doctor 查 when
verify: uv run pytest tests/core/test_schema.py tests/core/test_config.py tests/core/test_facets.py
applies: 实现或改 v0.7 边界校验时
---
需求来源：v0.7 设计稿 §3.4；复核时修提示路径与空 facets；再补 doctor 对 when/facets 的对照。

必须保持：
- schema 提供 SchemaError、expect_*、suggest_key、unknown_key_warnings；只用标准库。
- Config.load / ModuleRegistry 对未知键只警告（带相近键提示），不拒绝；嵌套未知键提示写成完整路径（如「是不是 gate.mode？」）。
- facets 写 null 或空键视为未启用（等同 {}），不报配置错误；超过 4 个维度警告。
- 配置类型错误报错带 .memory/config.yaml：字段路径。
- Entry 头类型错误带路径；when 非对象报错；对象里个别维度结构不对则跳过该维，保留其余；未知字段仍进 extra。
- Hook：validate_hook_payload 只警告；hook_cmd 记入 hook-errors.log 并放行。
- pmem doctor 汇总 config/modules 的警告，以及记忆 when 坏维（storage.warnings）与 when↔facets 不符。

入口：src/pmem/core/schema.py、config.py、registry.py、entry.py、facets.py；hooks/payload.py；cli/hook_cmd.py、doctor_cmd.py。
