---
id: 01M83NKQGDDSHBK8NDRBZX5C0S
module: feature.Onboarding
entity: Skills
kind: decision
status: active
supersedes:
- 01M52G7P3FMY0VYA8HHKYWF9WX
- 01M59G7FMN5H2D5EAZCADVAE3G
anchors:
- src/pmem/generate/integrations.py#_write_skills
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: init 写入 seed 与 consolidate，收口不自动合并
aliases:
- 技能
- 收口
source:
  kind: document
---
决定：pmem init 生成的项目技能包含 pmem-seed 与 pmem-consolidate，和 bootstrap、compact、normalize 一起写到各 Agent 的 skills 目录。

pmem-bootstrap 结尾提示接着「按 pmem-seed 技能提炼种子记忆」。
pmem-consolidate 不做自动合并，按 pmem health 编排：疑似矛盾写 correction 或 confirm；
过时则 confirm/correction/archive；
零碎交给 pmem-compact；
落空交给 pmem-normalize；
种子 seed --accept/--reject；
目录 migrate/sync 先预览再 --apply。
哪条仍成立要读代码，自动合并容易丢结论。

已接入项目要重新运行 pmem init 才得到新技能。doctor 计现行条数时，归档记忆的替代关系与检索口径一致。

合并自 2 条决定。技能必须保持的行为在同议题功能记录。
