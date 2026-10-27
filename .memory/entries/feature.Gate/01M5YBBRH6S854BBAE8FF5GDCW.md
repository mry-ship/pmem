---
id: 01M5YBBRH6S854BBAE8FF5GDCW
module: feature.Gate
entity: AnalysisWrap
kind: feature
status: active
supersedes:
- 01M5Y9TW095F8G6HP65JZ1S4G5
- 01M5YA61WSK15GKHGQRTW2T0V2
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/mcp.py#_note_cli_calls
revision: git:3a9f17f
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 结束提醒分三本账；声明只认修改行；排查不因改它模块漏催
verify: uv run pytest tests/hooks/test_gate.py tests/test_quality_efficiency.py -k
  "analysis_gap or handoff_wildcard or declar or consult_nudged"
applies: 回合结束 followup 与 CLI 检索去重
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
需求来源：2026-10-27 深度体检与用户要求减少 followup 打断，交付 commit 3a9f17f。

必须保持：
1) gate.analysis_reminder 缺省 false（DEFAULTS、init 模板、手册一致）；显式 true 时排查类查过未写仍催防错类，且改过别的模块也不豁免。
2) 功能记录、查阅/排查、规格各记 nudged / consult_nudged / spec_nudged；先催查阅后改代码仍催功能记录。
3) stop 从 transcript 解析【pmem修改】与旧【pmem】行；【pmem检索】【pmem查询】不参与。分段后去掉「标题」引号再匹配“无需记录”“无新结论”。无新结论按段点名只放过查阅/排查，不挡功能记录与提问审查。
4) stop_reminder 缺省仍为 true。
5) 终端 search/graph 有 --module/--path 但解析不出字面模块时登记 seen.HANDOFF_ANY（*），命令行按真实模块名仍可认领去重；细节见 infra.Common SeenHandoff。

入口：hooks/reminders.py（on_stop、_declarations、_pmem_declare_line、_segment_plain、_pending_analysis）；
hooks/mcp.py _note_cli_calls；
hooks/state.py consult_nudged；
core/seen.py claim_handoff。
