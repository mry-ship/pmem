---
id: 01M5YJ45YGKR6S4C4WXP1DRACR
module: feature.Gate
entity: AnalysisWrap
kind: feature
status: active
supersedes:
- 01M5YBBRH6S854BBAE8FF5GDCW
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/mcp.py#_note_cli_calls
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 结束提醒分三本账；声明只认修改行；CLI 仅变量才 * 交接
verify: uv run pytest tests/hooks/test_gate.py tests/test_quality_efficiency.py -k
  "analysis_gap or handoff or unresolved_module or declar"
applies: 回合结束 followup 与 CLI 检索去重
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
需求来源：2026-10-27 深度体检与结束提醒交付。
必须保持：
1) gate.analysis_reminder 缺省 false；显式 true 时排查类查过未写仍催防错类，改过别的模块也不豁免。
2) 功能记录、查阅/排查、规格各记 nudged / consult_nudged / spec_nudged；先催查阅后改代码仍催功能记录。
3) stop 只解析【pmem修改】与旧【pmem】行；分段后去掉「标题」再匹配无需记录/无新结论。无新结论只放过查阅/排查，不挡功能记录与提问审查。
4) stop_reminder 缺省仍为 true。
5) 终端 search/graph 仅当 --module/--path 是 Shell 变量时登记 HANDOFF_ANY；拼错模块名不当通配。闸门登记仍须字面模块名。细节见 infra.Common SeenHandoff。
入口：hooks/reminders.py on_stop；hooks/mcp.py _note_cli_calls；core/seen.py looks_like_shell_var。
