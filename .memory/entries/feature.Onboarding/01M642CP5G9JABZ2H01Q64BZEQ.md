---
id: 01M642CP5G9JABZ2H01Q64BZEQ
module: feature.Onboarding
entity: LazyDoctor
kind: exclusion
status: active
supersedes:
- 01M64181FENSN46V4BD8HA51KH
anchors: []
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 不要在 Hook 进程里跑完整自检，也不要把体检全文塞进对话
verify: uv run pytest tests/test_lazy_doctor.py -k unknown_event -q
applies: 本仓库 pmem 懒医生
aliases:
- inspect_only
- 不自动收拾
---
排除：不要每次 Hook 都在当前进程里跑完整 doctor；不要让懒医生自动改记忆文件或 modules.yaml；不要把「pmem 自检」全文塞进 additional_context 或 stop 的 followup。
原因：Hook 每次调用都有固定开销，完整自检还可能预热语义模型；用户要的是后台多触发、有问题提一句，不是对话里刷体检，也不是自动收拾记忆库。
适用条件：本仓库 pmem 懒医生。
