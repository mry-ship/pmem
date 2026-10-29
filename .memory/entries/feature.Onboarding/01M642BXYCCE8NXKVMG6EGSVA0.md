---
id: 01M642BXYCCE8NXKVMG6EGSVA0
module: feature.Onboarding
entity: LazyDoctor
kind: feature
status: active
supersedes:
- 01M6417N7RGDTD3B4JCVCBGYAA
anchors:
- src/pmem/cli/doctor_cmd.py#maybe_lazy_doctor_on_hook
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:e6c9bfc
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 本仓库懒医生每24小时后台巡检一次，Hook 有问题才提一行
verify: uv run pytest tests/test_lazy_doctor.py tests/test_cli_flow.py -q
applies: 接入了 pmem Hook 的项目；不是 pmem-art 的美术懒医生
aliases:
- 记忆医生
- 懒医生
- lazy doctor
---
需求来源：用户要求本仓库也做一套记忆医生，不要只改姊妹仓库 pmem-art。
必须保持：pmem 懒医生只检查不改库（状态写本机缓存 last_doctor.json，不改 entries / modules.yaml / config.yaml）；
前台 `pmem doctor` 仍打印自检、有 ✘ 退出 1、仅警告退出 0；
对外 help 仍只有 --root。
现行行为：距上次成功静默体检满 24 小时，session / prompt / pre-tool / post-tool / edited / stop 后台拉起 `pmem doctor --quiet`（不预热语义模型）。
有 ! 或 ✘ 时每天最多往 Hook 塞一行「🩺 记忆医生：…（可 pmem doctor）」。
崩溃子进程不写 last_run。
PMEM_NO_LAZY_DOCTOR 关闭。
测试夹具默认关闭，避免拉起后台进程。
适用条件：接入了 pmem Hook 的项目；不是 pmem-art 那套美术懒医生。
入口：src/pmem/cli/doctor_cmd.py 的 maybe_lazy_doctor_on_hook / run_doctor；闸门只负责抢槽。
更正：此前只把懒医生做成 pmem-art 的事，本仓库的 pmem doctor 也可以后台巡检。
