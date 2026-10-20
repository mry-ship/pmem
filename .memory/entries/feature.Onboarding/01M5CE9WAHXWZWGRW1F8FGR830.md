---
id: 01M5CE9WAHXWZWGRW1F8FGR830
module: feature.Onboarding
entity: Skills
kind: feature
status: active
supersedes:
- 01M5CCETHN0CXX8QTB2FCPE0X3
anchors:
- src/pmem/generate/templates.py
- src/pmem/scan/files.py#code_mentions
revision: git:d6b5bd7
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 收口技能处理跳过复查、清理候选、转正与召回偏低，归档须用户确认
verified: '2026-10-20'
verified_at: '2026-10-20T19:03:59.331+08:00'
---
需求来源：v0.3.2、v0.4 给 pmem health 新增了跳过复查、清理候选、未登记模块的建议 paths、召回偏低（GitHub Issue #13、#14），收口技能要会处理。
必须保持的行为：
- pmem-consolidate 技能处理“改了代码却没写功能记录”（问需求，有用户要求的行为就补 feature）和“建议归档 / 清理待核对”：建议归档要先给用户确认再 pmem archive，不能自己直接归档；
  排除项、风险、更正即使代码删了也默认保留。
- 未登记模块确属新业务时登记报告建议的 paths，冷候选用 pmem sync --apply 转正；
  召回偏低的模块先看从没返回的议题，补 aliases 或同义词，议题太杂的给用户看 migrate split --by entity 的预览。
- pmem-compact 技能写明合并错了用 pmem compact --undo 撤销。
- 正文提及解析 code_mentions 只认源码文件和带目录的路径，供清理候选使用。
入口：src/pmem/generate/templates.py 的 CONSOLIDATE_SKILL、COMPACT_SKILL；src/pmem/scan/files.py 的 code_mentions。
