---
id: 01M7X8621PSWARFWET86V29QX3
module: infra.Common
entity: Provenance
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/brief.py#_provenance
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: record 增加来源和生效日，brief 附出来源
verify: uv run pytest tests/test_spec_closed.py tests/test_quality_efficiency.py::test_brief_marks_seen_rows_and_shows_verify
aliases:
- 来源种类
- source-kind
- valid-from
---
需求来源：来源种类和生效日的命令行入口。

必须保持：
- pmem record 有 --source-kind 和 --valid-from。帮助里写明不表示已核对、不参与排序；覆盖草稿时不写或写空则沿用原值，不能清空。
- pmem spec 的动作增加 closed。--module 只用于 spec closed，别的动作带它退出码 2。
- brief 在结果下另起一行写来源、未核对和生效日。标题行不变。需核实仍只由过时锚点打出。

入口：src/pmem/cli/main.py、spec_cmd.py、brief.py。
