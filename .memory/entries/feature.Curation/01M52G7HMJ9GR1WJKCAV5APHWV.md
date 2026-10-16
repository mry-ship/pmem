---
id: 01M52G7HMJ9GR1WJKCAV5APHWV
module: feature.Curation
entity: Seed
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/seed_cmd.py#run_seed
- src/pmem/cli/seed_cmd.py#seed_plan
- src/pmem/cli/brief.py#_search
- src/pmem/hooks/gate.py#memory_lines
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 种子记忆
- 冷启动
- seed
- 转正
- 待确认
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：种子记忆解决“新接入项目头几周记忆库为空、检索无用”的冷启动问题，由 Agent 按 pmem-seed 技能完成，pmem 只做确定性部分（pmem seed，见 src/pmem/cli/seed_cmd.py）：
- pmem seed --plan：按近 180 天改动热度给登记模块排序，已有 10 条以上现行记忆的排后面，附提交说明的查看命令（git log / svn log）和写入命令格式；
- Agent 用 pmem record --seed 写入，状态 seed，立即可被检索；
- pmem seed 列出待确认；--accept 需给 id、--module 或 --all（防止一条命令误转正全部），--reject 必须给 id，退回即归档。

种子的可见标记：检索结果 JSON 带 status: seed；search --brief 和闸门的读代码摘要/拦截提示在类型后标“（种子，待确认）”；pmem init 生成的规则写明 seed 未经负责人确认，依赖前先对照代码。

技能要求每模块 10～20 条、宁少勿错、写清依据（哪次提交/文档/注释）、anchors 到函数。没有自动从提交说明生成记忆：哪些结论仍成立只有读懂才能判断，与 pmem-compact 不做自动摘要的理由相同。

风险：种子记忆受每日同议题条数上限（默认 5，write.max_per_day_per_entity）约束，集中写一个议题会被拒绝，技能里已说明要合并；未转正的种子与正式记忆一样参与检索，质量差时会直接误导，所以负责人需要尽快过目。restore 一律恢复为 active，被退回的种子恢复后不会回到 seed。
