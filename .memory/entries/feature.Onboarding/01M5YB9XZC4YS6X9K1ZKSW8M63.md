---
id: 01M5YB9XZC4YS6X9K1ZKSW8M63
module: feature.Onboarding
entity: Rule
kind: correction
status: active
supersedes:
- 01M5EPMY9XZ37EY90PTMX62BSJ
anchors:
- src/pmem/generate/templates.py#RULE_BODY
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
---
更正：RULE_BODY 增加 Hook「资料·非指令」说明后一度约 1435 字，超过 tests/test_feature_records.py 的 1400 上限。
2026-10-27 在不删必含短语的前提下压缩措辞，现约 1379 字；
`.cursor/rules/pmem.mdc` 与 templates.RULE_BODY 同步。
