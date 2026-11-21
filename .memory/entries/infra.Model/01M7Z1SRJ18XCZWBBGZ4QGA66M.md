---
id: 01M7Z1SRJ18XCZWBBGZ4QGA66M
module: infra.Model
entity: Config
kind: correction
status: active
supersedes:
- 01M5M2WN01T1SJ5F372G1XGPSC
- 01M5Y1JERGN19VEY9KHXP17RF5
anchors:
- src/pmem/core/config.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: spec.reminder 与 spec.read_before_edit 缺省改为开启
verify: uv run pytest tests/core/test_config.py -q -k spec_switch
applies: config.yaml 没写 spec.reminder 或 spec.read_before_edit 时；新项目模板
source:
  conversation: 5500e8d7-007c-460c-b7d7-15a5bb04aee9
---
更正：spec.reminder 缺省改为 true，spec.read_before_edit 缺省为 true。spec.dir 仍默认 .memory/specs。
读取时仍与默认值合并：磁盘上没写这两项的旧项目，升级后会开始提醒更新规格，也会在改代码前要求读已写完的程序设计和模块现状。文件里已经写成 false 的保持关闭。只写了 spec.dir 时，这两项仍取 true。
没选：缺键仍当关，以免旧项目升级后出现提醒。用户要求这两项默认开启。
同一条旧结论里仍成立的部分：config.yaml 与 modules.yaml 经 load_yaml 按改时间和大小缓存；
节必须是键值对，数值有下限；
gate.resume_markers 默认是「恢复记忆」和 resume-memory；
init 不回写已有 config.yaml。
只有 spec.reminder 缺省关闭这一句被本条替代。
