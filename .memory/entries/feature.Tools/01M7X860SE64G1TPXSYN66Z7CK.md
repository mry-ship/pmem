---
id: 01M7X860SE64G1TPXSYN66Z7CK
module: feature.Tools
entity: Provenance
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 写入可带来源和生效日，检索契约要校验
verify: uv run pytest tests/test_service.py::test_provenance_survives_every_rewrite
aliases:
- 来源种类
- source.kind
- valid_from
---
需求来源：来源和生效日写入后，任何一次写回都不能把 source 里的字段丢掉。

必须保持：
- record 接受 source_kind、valid_from。非法值返回 source_kind_invalid、valid_from_invalid。
- 覆盖草稿时 kind、valid_from、conversation 不传或空串都沿用。传了新对话 id 才替换。
- 核对、归档、恢复、种子转正与退回、撤销、format、anchors、rename、migrate move 写回后，这三项仍在文件里。回归要读回文件再解析，不能只看检索行。
- 检索行必须有 source_kind。没有 verified 时 unverified 为 true。已核对不能再标 unverified。
- 字段说明只在 record_memory、pmem record --help 和每个对话一次的 source_hint。需核实仍只指过时锚点。

入口：src/pmem/service/record.py、status.py；tests/test_service.py::test_provenance_survives_every_rewrite。
