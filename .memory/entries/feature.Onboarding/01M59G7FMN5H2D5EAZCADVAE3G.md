---
id: 01M59G7FMN5H2D5EAZCADVAE3G
module: feature.Onboarding
entity: Skills
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/integrations.py#_write_skills
revision: git:1e8fc87
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- consolidate
- 收口
- 整理记忆库
- 技能
- skill
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:14.279+08:00'
---
决定：pmem init 生成的项目技能新增 pmem-consolidate（模板 CONSOLIDATE_SKILL），与 bootstrap、compact、normalize、seed 一起写到各工具的 skills 目录。
它是 v0.2 consolidate 的落地方式：不做自动合并，而是让 Agent 按 pmem health 的各节依次收口：
- 疑似矛盾：写 correction 替代，或 confirm 较早那条；
- 可能过时：confirm、correction 或 archive；
- 零碎与相近议题：交给 pmem-compact；检索落空交给 pmem-normalize；
- 种子：seed --accept/--reject；
- 模块目录：migrate merge/tidy/split 与 sync 先预览、用户确认后 --apply。

原因：哪条结论仍成立只有读懂代码才能判断，自动合并容易丢结论；合并与同义词已有技能，这里只做编排。
影响：已接入的项目重新运行 pmem init 才有新技能；本仓库的 .cursor/skills/pmem-consolidate 已按模板生成。技能里的命令都已对照 CLI 帮助核对。
