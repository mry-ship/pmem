---
id: 01M521A2HVVXE5Y4MHR03X1SX8
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 覆盖草稿
- 清空别名
verified: '2026-10-19'
---
决定：pmem record 的 --supersedes / --anchor / --alias 默认值改为“没传”（None），并允许只写参数名不跟值。
配合 --draft-id 时：不写沿用草稿原值，只写参数名表示清空，写了值则替换。

原因：原先默认是空列表，覆盖草稿时不重写这些参数就会清空替代关系，旧记忆重新变成现行。

风险：脚本里如果写了 --alias 却不跟值（原先会报参数错误），现在会被当成清空。
