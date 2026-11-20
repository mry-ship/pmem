---
id: 01M7WKS0CN5RQCBX1E457G07YJ
module: feature.ModuleCatalog
entity: Schema
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: modules.yaml 未知键警告进 registry.warnings
verify: uv run pytest tests/core/test_registry_paths.py；doctor 可见拼错键警告
applies: 改 modules.yaml 校验或 doctor 汇总警告时
---
需求来源：v0.7 §3.4 边界校验；modules.yaml 拼错键原先静默忽略，doctor 看不到。

必须保持：
1) ModuleRegistry 加载时对顶层及 modules/candidates 条目未知键只警告不拒绝，提示相近键名（已忽略）；节类型不对仍报 RegistryError 并带字段路径。
2) 警告挂在 registry.warnings，供 pmem doctor 汇总打印。
3) 认识的模块体键仍是 paths/aliases/entities/components/variants/parent/related/status/description。

入口：src/pmem/core/registry.py（ModuleRegistry）；pmem doctor。
