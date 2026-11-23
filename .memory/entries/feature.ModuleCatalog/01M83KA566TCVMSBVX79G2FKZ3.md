---
id: 01M83KA566TCVMSBVX79G2FKZ3
module: feature.ModuleCatalog
entity: ModulesSchema
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#_MODULES_TOP
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: modules.yaml 认 schema_version 顶层键
verify: uv run pytest tests/core/test_registry_names.py -q -k schema_version
source:
  kind: code
---
需求来源：doctor 报 modules.yaml 不认识 schema_version，但规格与模板顶层键已列该字段。

必须保持：ModuleRegistry 解析 modules.yaml 时，顶层 schema_version 是已知键，不再警告「不认识的键 schema_version」；数值不参与校验，只被忽略。其余顶层键与模块体字段闭集不变。

入口：src/pmem/core/registry.py#_MODULES_TOP；pmem doctor。
