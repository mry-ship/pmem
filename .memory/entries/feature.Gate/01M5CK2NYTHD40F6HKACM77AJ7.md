---
id: 01M5CK2NYTHD40F6HKACM77AJ7
module: feature.Gate
entity: AutoAnchors
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/payload.py#_extract
- src/pmem/hooks/mcp.py#_inject
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 载荷只部分解析时原先抠不到 kind，功能记录拿到教训的草稿 id 并覆盖了教训
verify: uv run pytest tests/hooks/test_gate.py -k partly_parsed_feature
aliases:
- 草稿覆盖
- 记忆被覆盖
- 分层失效
- _partial
---
根因：Hook 输入被转码损坏、只能按字段抠取（_partial）时，抠取清单里原先没有 kind。闸门据此把功能记录当成教训一层，注入了同议题教训的草稿 id，功能记录直接覆盖了那条教训。
证据：2026-10-20 写 feature.Metrics/Report 功能记录时，hooks.log 里 updated_input 带上了同议题结论 01M5CGYGZ6X3D3Z3T5XJS714VB 的 draft_id，那条结论被改写成功能记录；
随后写的更正又替代了它，功能记录也被隐藏。
已恢复原文，并重写功能记录。
修复：抠取清单加入 kind（值是 ASCII，不受转码影响）。
仍有的风险：抠取清单之外的字段（如 supersedes、anchors 这类列表）在部分解析时仍看不到；依赖它们判断的注入逻辑都要先看 _partial。
