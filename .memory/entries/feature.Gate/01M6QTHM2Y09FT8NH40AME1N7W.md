---
id: 01M6QTHM2Y09FT8NH40AME1N7W
module: feature.Gate
entity: LazyDoctor
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/lazy_doctor.py#maybe_lazy_doctor_on_hook
- src/pmem/hooks/gate.py#_lazy_doctor
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 懒医生从 hooks 调用，不再越层依赖 cli
verify: uv run pytest tests/test_layering.py tests/test_lazy_doctor.py -q
---
需求：分层测试 hooks/gate 不得依赖 cli；闸门仍要跑懒医生。
行为：maybe_lazy_doctor_on_hook 与抢槽/spawn/tip 迁到 src/pmem/hooks/lazy_doctor.py；
gate 从 hooks 包调用；doctor_cmd 再导出同名 API 供 CLI/测试。
后台仍用字符串拉起 pmem.cli.main，不在 hooks 里 import cli。
入口：hooks/gate._lazy_doctor；pmem doctor --quiet。
