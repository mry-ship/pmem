---
id: 01M5Y51P9WPSA81REYAD5RX2E6
module: feature.Gate
entity: AnalysisWrap
kind: conclusion
status: active
anchors:
- src/pmem/hooks/reminders.py#_pending_analysis
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 排查收口缺口根因：analyzed 只记日志，有 edited 时不发查阅提醒
verify: uv run pytest tests/hooks/test_gate.py -k analysis_gap
applies: 解释 analysis_left 偏高或排查不落 exclusion 时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
现象：report 显示排查类对话结束仍有查过却没写的模块（analysis_left），但 Agent 常收不到结束提醒。
根因：_analyzed 只写入 stop 事件供报告统计；
真正发 followup 的是 _consulted_only，它在「本对话有任何 edited 或 written」时直接返回空。
排查时查了模块 A、却改/写了模块 B，A 的缺口只进报告、不催写。
处理：新增 _pending_analysis，在 analysis 标记下对 _analyzed 缺口发强制防错类收口提醒，与是否改过其他模块无关。
证据：TileMatch/本仓库 report 习惯节与 tests/hooks/test_gate.py::test_analysis_gap_reminded_even_if_other_module_written。
