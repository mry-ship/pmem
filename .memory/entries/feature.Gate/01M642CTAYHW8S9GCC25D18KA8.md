---
id: 01M642CTAYHW8S9GCC25D18KA8
module: feature.Gate
entity: LazyDoctor
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_lazy_doctor
- src/pmem/hooks/reminders.py#on_stop
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: Hook 只抢槽后台拉起懒医生，提示不进 stop followup
verify: uv run pytest tests/test_lazy_doctor.py tests/hooks/test_gate.py -q
applies: 未设置 PMEM_NO_LAZY_DOCTOR
aliases:
- 记忆医生
- 懒医生
---
需求来源：本仓库要有记忆医生，触发挂在现有 Cursor/Claude/Codex Hook 上。
必须保持：Gate 里只做毫秒级 claim 和 Popen，不在 Hook 进程里跑完体检；
stop 的 followup 仍只用于未查/没写记忆/规格等原有提醒，不附完整体检。
session 无提示时仍返回空对象，包装脚本找不到 pmem 时的安装提示不受影响。
Autosync 的 session/edited 后台扫描行为不变。
pre-tool / prompt / edited / stop 只抢槽，不消费每日提示。
现行行为：session、prompt、pre-tool、post-tool、edited、stop 调用 maybe_lazy_doctor_on_hook；
高信号提示只写在 session 与 post-tool 的 additional_context（与 error_notice、autosync.take_notice 并列）。
适用条件：未设置 PMEM_NO_LAZY_DOCTOR。
入口：src/pmem/hooks/gate.py 的 _lazy_doctor；src/pmem/hooks/reminders.py 的 on_stop。
