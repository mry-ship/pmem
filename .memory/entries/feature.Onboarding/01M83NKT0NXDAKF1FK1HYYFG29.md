---
id: 01M83NKT0NXDAKF1FK1HYYFG29
module: feature.Onboarding
entity: Skills
kind: feature
status: active
supersedes:
- 01M5CE9WAHXWZWGRW1F8FGR830
- 01M5KV8EYC94KA97JJ6QBBMJT7
- 01M640GYMG4FPVB84Y6Q3DZS6T
anchors:
- src/pmem/generate/templates.py
- src/pmem/scan/files.py#code_mentions
- src/pmem/generate/integrations.py#_write_skills
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 收口、规格技能与 compact 保持防错类型
aliases:
- pmem-spec
- pmem-compact
- pmem-consolidate
source:
  kind: document
---
需求来源：health 收口、模块规格技能、compact 不要把防错类收成结论。

必须保持：
- pmem-consolidate：处理「改了代码却没写功能记录」（有用户要求的行为就补 feature）和清理候选。
  建议归档先给用户确认再 archive，不能自己直接归档。
  排除项、风险、更正即使代码删了也默认保留。
  未登记模块确属新业务时登记建议 paths；
  冷候选 pmem sync --apply。
  召回偏低先看从没返回的议题，补 aliases 或同义词；
  议题太杂给用户看 migrate split --by entity 的预览。
- pmem-compact：合并错了用 pmem compact --undo。
  exclusion / risk / correction 合并后保持这三类，不要收成 conclusion；
  其余用 conclusion 或 decision。
  模板经 str.format，正文花括号写成 {{ }}。
  已接入项目要重跑 init 或同步技能才会拿到新文案。
- pmem-spec：init 写到各 Agent 技能目录。
  四份文件名、美术不放代码路径、无画面写「本模块无画面」、一句一行、父模块不写子模块正文、不写「这一轮只新增」、当轮更新不整篇重写、写前 search_memory。
  用户说「补全模块规格」或 pmem spec fill/complete 时按首稿写全列出的模块。
  已有 config.yaml 不被 init 改写。
  模块已登记时只补还没有的骨架，不写正文。
- code_mentions 只认源码文件和带目录的路径，供清理候选使用。

入口：generate/templates.py 的 CONSOLIDATE_SKILL、COMPACT_SKILL、规格技能；integrations._write_skills；scan/files.py code_mentions。

合并自 3 条功能记录。
