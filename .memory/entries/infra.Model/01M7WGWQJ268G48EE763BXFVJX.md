---
id: 01M7WGWQJ268G48EE763BXFVJX
module: infra.Model
entity: WhenFacets
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: config 可声明 facets；记忆写 when，按声明校验
verify: uv run pytest tests/core/test_facets.py
applies: 实现或改 v0.7 结构化适用条件时
---
需求来源：v0.7 设计稿 §3.3（Issue #15）。

必须保持：
- config.yaml 可声明 facets：维度值为枚举列表，或 str（任意非空文字）。
- Entry 可选字段 when: {维度: [取值]}；写入按 facets 校验（未知维度、非法取值报 when_invalid）；未声明 facets 时传 when 拒绝。
- 取值大小写不敏感，写入收成声明里的规范写法；单值可写成标量，读盘收成列表。
- applies 保留给无法枚举的前提；能用 facets 表达的优先写 when。

入口：src/pmem/core/facets.py、src/pmem/core/config.py、src/pmem/core/entry.py、src/pmem/service/record.py。
