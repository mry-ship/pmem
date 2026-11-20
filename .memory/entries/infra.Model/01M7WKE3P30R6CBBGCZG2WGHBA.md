---
id: 01M7WKE3P30R6CBBGCZG2WGHBA
module: infra.Model
entity: WhenFacets
kind: feature
status: active
supersedes:
- 01M7WGWQJ268G48EE763BXFVJX
anchors:
- src/pmem/core/facets.py#when_structure_issues
- src/pmem/storage/files.py
- src/pmem/cli/doctor_cmd.py#_check_when_facets
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: config 可声明 facets；记忆写 when，读盘坏维跳过并告警
verify: uv run pytest tests/core/test_facets.py
applies: 实现或改 v0.7 结构化适用条件时
---
需求来源：v0.7 设计稿 §3.3；复核时明确读盘行为；再修「静默丢维」可观测性。

必须保持：
- config.yaml 可声明 facets：维度值为枚举列表，或 str（任意非空文字）；facets 为 null/空键视为未启用。
- Entry 可选字段 when: {维度: [取值]}；写入按 facets 校验（未知维度、非法取值报 when_invalid）；未声明 facets 时传 when 拒绝。
- 取值大小写不敏感，写入收成声明里的规范写法；单值可写成标量，读盘收成列表。
- 读盘：when 非对象报错；对象里个别维度结构不对则跳过该维，不拖垮其余合法维。
- 跳过不能静默：when_structure_issues 列出坏维；
  FilesStorage.iter_all 写入 warnings；
  pmem doctor 打印这些警告，并对照 facets 报告「有 when 未声明 facets」或「when 与 facets 不符」。
- applies 保留给无法枚举的前提；能用 facets 表达的优先写 when。

入口：src/pmem/core/facets.py、src/pmem/core/config.py、src/pmem/core/entry.py、src/pmem/storage/files.py、src/pmem/cli/doctor_cmd.py、src/pmem/service/record.py。
