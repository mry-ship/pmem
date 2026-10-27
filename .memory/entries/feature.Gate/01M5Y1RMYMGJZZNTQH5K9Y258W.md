---
id: 01M5Y1RMYMGJZZNTQH5K9Y258W
module: feature.Gate
entity: Agents
kind: conclusion
status: active
supersedes: []
anchors:
- tests/hooks/test_agents.py
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: Claude/Codex 归一化单测 13 项通过；真实会话抽检仍待人工
verify: pytest tests/hooks/test_agents.py -q
applies: 评估 Claude/Codex 集成是否可发版时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
结论：2026-10-27 跑 tests/hooks/test_agents.py 共 13 项通过（含 Codex prompt 摘要、Claude PowerShell 按终端拦截）。
仍有效的已知限制：未在真实 Claude Code / Codex 交互会话里端到端跑闸门+检索+写入。
处理：单测当作回归底线；实机会话抽检留作发版前人工清单（提问附摘要、Shell/PowerShell 写文件拦截、Stop followup）。
