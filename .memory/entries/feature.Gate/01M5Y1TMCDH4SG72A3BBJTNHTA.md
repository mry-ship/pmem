---
id: 01M5Y1TMCDH4SG72A3BBJTNHTA
module: feature.Gate
entity: DraftInjection
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
revision: git:26581ff
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 同议题 feature 与 plan 同层：后写会 draft 覆盖先写，开工记录与规划要拆议题或分两次提交
verify: 先写 feature 再写同议题 plan 且未提交时，第二次返回 overwritten 且 id 相同
applies: 同议题既写 feature 又写 plan 时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
现象：同一任务先后 MCP 写 Roadmap 的 feature 与 plan，闸门按同模块同议题同一层注入同一 draft_id，后写覆盖先写；提交后再想改会 draft_forbidden。
根因：feature/plan 同属 RECORD 层，AutoAnchors 按层去重草稿。
处理：同议题既要功能记录又要规划时，换议题名（如 RoadmapKickoff / Roadmap），或先提交一条再写另一条；覆盖错了就新建并 supersedes。
证据：本轮 01M5Y1RHJCTVAS6XRJNX441PN8 在 feature↔plan 间被覆盖，后补 01M5Y1SRC18WCERGWZXSCTKMC1 为 plan。
