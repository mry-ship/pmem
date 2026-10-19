---
id: 01M5A1KDQ5SPRR50DHRTZEG4T6
module: feature.Import
entity: LanceDB
kind: decision
status: active
supersedes: []
anchors:
- tests/importers/test_lancedb_import.py
- src/pmem/core/ids.py#ulid_ms
revision: git:c515ce0
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 导入
- ULID 时间
- ulid_ms
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：导入测试改从 core.ids 取 ulid_ms（ULID 生成时间），不再从 index.store 导入；该函数已移到 core/ids.py（见 infra.Model / Ulid）。
原因：导入功能本身只依赖 core、storage、catalog，测试为一个小函数加载检索索引和 numpy 没有必要，也与 tests/test_layering.py 的分层规则不一致。
影响：只改了测试的导入位置，导入行为不变（按源 created_at 生成 ULID、保留新旧顺序），相关测试通过。
风险：无；以后导入代码要用 ULID 时间时同样从 core.ids 取。
