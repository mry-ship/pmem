---
id: 01M7WHP5R8RP2QWX8TQBQNM2JZ
module: feature.Tools
entity: Contracts
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 工具返回 TypedDict 契约与形状检查测试
verify: uv run pytest tests/service/test_contracts.py
applies: 改 search/record/graph/list_modules 返回字段时
---
需求来源：v0.7 设计稿 §3.5。

必须保持：
- service/contracts.py 用 TypedDict 登记 search/record/graph/list_modules 返回字段。
- check_search/record/graph/list_modules 供测试校验真实返回；字段改名、漏写、类型变了失败。
- 失败返回须有 error 字符串。

入口：src/pmem/service/contracts.py；tests/service/test_contracts.py。
