---
id: 01M642JZ5CJ3APX2C2D4QXM3D2
module: feature.Onboarding
entity: LazyDoctor
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/cli/doctor_cmd.py#maybe_lazy_doctor_on_hook
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 只在 session 和 post-tool 取出医生提示，免得 pre-tool 吃掉还不展示
verify: uv run pytest tests/test_lazy_doctor.py -k eat_pending -q
applies: 本仓库 pmem 懒医生
---
现象：session / prompt / pre-tool / edited / stop 都会抢懒医生槽，若每次都 consume 提示，真正会交给 Agent 的只有 session 和 post-tool。
Cursor 下一轮几乎总是先 pre-tool，会把「🩺 记忆医生」一行吃掉却不展示，用户以为医生没说话。
原因：maybe_lazy_doctor_on_hook 把抢槽和取提示绑在一起，调用方丢掉返回值时提示已经 tip_pending=false。
处理：抢槽事件与取提示事件分开。DOCTOR_TIP_EVENTS 只有 session、post-tool。
影响：pre-tool / prompt / edited / stop 只后台拉起，不消费每日提示额度。
