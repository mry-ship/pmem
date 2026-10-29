---
id: 01M6417N7RGDTD3B4JCVCBGYAA
module: feature.Onboarding
entity: LazyDoctor
kind: feature
status: active
supersedes: []
anchors: []
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 记忆医生每24小时最多巡一次；生图前后、新对话和 converge finish 都会抢槽
verify: 在 Cursor-Pmem-Art 跑 python -m unittest tests.test_lazy_doctor -v
applies: 姊妹仓库 Cursor-Pmem-Art 的懒医生，不是本仓库的 pmem doctor 命令
aliases:
- 记忆医生
- lazy doctor
- 懒医生
---
需求来源：用户发现记忆医生几乎不跑，要求稍微加强、多几个触发时机。
必须保持：pmem-art 的懒医生仍是只检查不改库（只写 last_doctor.json，不改 entries / modules.yaml / 资产）；Hook 不倾倒完整体检；有问题最多一行小提示，且走每日 tip_budget。
现行行为：间隔 24 小时才抢一次后台巡检；
可抢槽事件包括生图前（pre-tool/pre-gen）、落盘后（post-tool/post-asset）、对话结束（stop）、新开对话（sessionStart → hook session）、以及 CLI converge finish。
未列入的事件只消费已写好的高信号提示。
崩溃的后台子进程不写 last_run_at，避免烧掉整个 24 小时窗口。
适用条件：这是姊妹仓库 Cursor-Pmem-Art 的懒医生，不是本仓库命令行 `pmem doctor`。用户主要在本仓库干活、pmem-art 的 Cursor Hook 不常触发时，单靠生图前/stop + 48 小时会长期不跑。
入口：Cursor-Pmem-Art 的 lifecycle.maybe_lazy_doctor_on_hook、converge finish、.cursor/hooks.json 的 sessionStart。
