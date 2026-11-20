---
id: 01M7WTATGM87QPCV6NT8QBZTQ4
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes:
- 01M7WH96WMRQZBFFW2K4WD5DM4
anchors:
- src/pmem/cli/doctor_cmd.py#_check_when_facets
- src/pmem/cli/doctor_cmd.py#_run_doctor_body
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: doctor 汇总拼错键、Hook 警告与 when/facets 对照
verify: uv run pytest tests/test_cli_flow.py::test_doctor_warns_when_without_facets_and_bad_when
  -q
applies: 改 doctor 输出或 when/facets 自检时
---
需求来源：v0.7 §3.4 doctor 汇总；复核补 when/facets 可见性与单测。

必须保持：
- 配置/modules 拼错键与 facets 过多提示出现在 pmem doctor；Hook 字段类型不对写入 hook-errors.log，doctor 近 24 小时能看到。
- 现行记忆写了 when 但未声明 facets → 警告「检索不会按 when 过滤」；when 与 facets 不符 → 警告；最多展示 8 条并截断提示。
- storage.warnings（含 when 坏维跳过）前几条打印，超出提示另有条数。

入口：cli/doctor_cmd.py#_check_when_facets、_run_doctor_body；
测试 tests/test_cli_flow.py::test_doctor_warns_when_without_facets_and_bad_when。
