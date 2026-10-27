---
id: 01M5Y51BQTZ6E2PH43N5MAGHVH
module: feature.Gate
entity: AnalysisWrap
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#_pending_analysis
- src/pmem/hooks/reminders.py#on_stop
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 排查类对话查过未写的模块结束必催防错类；改过别的模块也不豁免
verify: uv run pytest tests/hooks/test_gate.py -k "consulted or analysis_gap or declar"
applies: 回合结束、analysis_reminder 未关且非 skip/中断时
aliases:
- 排查收口
- 防错类提醒
- analysis_left
verified: '2026-10-27'
verified_at: '2026-10-27T15:55:04.467+08:00'
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：按本仓库与 TileMatch 的 report，排查对话收口缺口（查过却没写）与防错类占比偏低。
必须保持：
1) 提问命中 analysis_markers 且 gate.analysis_reminder 开启时，查过却既没改代码也没写记忆的模块在 stop 发 followup（每条以 [pmem] 开头），文案要求优先写 exclusion，其次 risk/conclusion/correction；
   确认无结论时须在【pmem修改】行写「已核对，无新结论」（ReplyDeclaration 只认该前缀）。
2) 即使本轮改写了别的模块，上述缺口模块仍提醒（不再被「有 edited/written」整段关掉）。
3) 回复【pmem…】行声明「无新结论」时不发本条与纯查阅提醒（ReplyDeclaration 不变）。
4) 非排查、整段只查不改不写的对话仍走较软的查阅提醒，并提示优先防错类；无结论同样写在【pmem修改】行。
5) 改代码未写功能记录的提醒里，教训一段标明优先防错类；无需记录须写在【pmem修改】行。
入口：src/pmem/hooks/reminders.py（_pending_analysis、on_stop）。
