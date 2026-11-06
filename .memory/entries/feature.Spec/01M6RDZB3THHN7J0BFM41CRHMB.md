---
id: 01M6RDZB3THHN7J0BFM41CRHMB
module: feature.Spec
entity: SpecPrefill
kind: feature
status: active
supersedes:
- 01M6RD5N8F0KX38YRG5Q3R9PEW
anchors:
- src/pmem/generate/spec.py#spec_prefill
- src/pmem/generate/spec.py#_prefill_lines
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 规格预填把带换行的锚点收成一条列表项
verify: uv run pytest tests/test_spec.py::test_prefill_anchor_newline_stays_one_bullet
  -q
applies: pmem spec init 或 fill 用现行 feature 记忆预填程序设计和模块现状
aliases:
- 锚点换行
- 程序设计
---
需求来源：规格预填把 feature 记忆的锚点原样写进程序设计.md 的入口。锚点里的换行会把列表拆开，后面的行不再是列表项。

必须保持：预填进「入口」和「必须保持」的每一条都是一行。锚点、summary、标题里的换行收成空格后再写列表；收成空串的跳过。EMPTY 标记仍留着，预填不等于首稿已完成。

入口：spec_prefill、_prefill_lines。
