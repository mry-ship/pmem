---
id: 01M5CCETHN0CXX8QTB2FCPE0X3
module: feature.Onboarding
entity: Skills
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/scan/files.py#code_mentions
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 收口技能处理跳过复查和清理候选，归档须用户确认；合并技能写明 --undo
---
需求来源：v0.3.2 新增 pmem health 的跳过复查和清理候选两节、合并回滚（Issue #13），收口技能要会处理。
必须保持的行为：
- pmem-consolidate 技能处理“改了代码却没写功能记录”（问需求、有用户要求的行为就补 feature）和“建议归档 / 清理待核对”：建议归档要先给用户确认再 pmem archive，不能自己直接归档；
  排除项、风险、更正即使代码删了也默认保留。
- pmem-compact 技能写明合并错了用 pmem compact --undo 撤销。
- 新的正文提及解析 code_mentions 只认源码文件和带目录的路径，供清理候选使用。
入口：src/pmem/generate/templates.py 的 CONSOLIDATE_SKILL、COMPACT_SKILL；src/pmem/scan/files.py 的 code_mentions。
