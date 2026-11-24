---
id: 01M866389SB3TGTZZJYY6V8RG9
module: infra.Model
entity: Config
kind: correction
status: active
supersedes:
- 01M7Z1SRJ18XCZWBBGZ4QGA66M
- 01M5M2WN01T1SJ5F372G1XGPSC
- 01M5Y1JERGN19VEY9KHXP17RF5
anchors:
- src/pmem/core/config.py
revision: git:183b8bc
author: 1002378395@qq.com
note_date: '2026-11-24'
summary: spec.reminder 与 spec.read_before_edit 缺省改回关闭
verify: uv run pytest tests/core/test_config.py -q -k spec_switch
applies: config.yaml 没写 spec.reminder 或 spec.read_before_edit 时；新项目模板
aliases:
- 规格提醒
- spec.reminder
- read_before_edit
source:
  conversation: af778473-37cc-4d1b-887c-4cef901acd49
  kind: human
valid_from: '2026-11-24'
---
更正：spec.reminder 与 spec.read_before_edit 缺省改回 false。spec.dir 仍是 .memory/specs。
原因：用户要求默认关上。只改新项目模板不够，读取时会并入 DEFAULTS；没写这两项的旧项目（含本仓库）升级后也要关掉。
读取时与默认值合并：磁盘上没写这两项的旧项目，升级后不再提醒更新规格，也不在改代码前要求读已写完的规格。只写了 spec.dir 时，这两项取 false。文件里已经写成 true 的保持开启，写成 false 的保持关闭。
没选：缺键仍当开，那会让没写配置的项目继续被提醒和拦截。
仍成立：config.yaml 与 modules.yaml 经 load_yaml 按改时间和大小缓存；
节必须是键值对，数值有下限；
gate.resume_markers 默认是「恢复记忆」和 resume-memory；
init 不回写已有 config.yaml。
