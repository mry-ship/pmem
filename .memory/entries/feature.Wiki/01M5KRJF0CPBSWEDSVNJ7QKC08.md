---
id: 01M5KRJF0CPBSWEDSVNJ7QKC08
module: feature.Wiki
entity: RebuildSpec
kind: plan
status: active
supersedes: []
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: v0.6 每个模块一份规格，改动的那一轮更新一次，单拿这份就能重做
applies: 还没实现。只拷走文档、不拷工程，仍要能按文档把单个模块在别处重做出来时。
aliases:
- 模块规格
- 策划设计
- 程序设计
- 可复用模块文档
- 模块蓝图
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
需求来源：用户（2026-10-23）。每个模块一份当前规格，与 Wiki 平级、进版本库。策划、程序、现状齐全，单拿这份就能在别处重做；不做记忆过期核对。
定为 v0.6（Issue #16）。
设计 docs/superpowers/specs/2026-10-23-pmem-module-spec-design.md，实施计划 docs/superpowers/plans/2026-10-23-pmem-module-spec.md。
命令行只做骨架、目录和漏更新提醒；
正文由 pmem-spec 技能写。
旧模块先做首稿：程序和现状按代码实现写。策划只写已体现在代码或资源里的数值、边界、表现、规则；没留下的完整策划稿留空。
更新不按时间：某一轮改了该模块或定了新策划，这一轮结束前更新这一份一次。程序与现状只改正波及的段落，当轮策划写入并保留。回合结束若改了模块却没更新规格，提醒一次。
新模块由 AI 做成时，策划当轮写入才算留下来。
没选：定时全量重写、每次写记忆都重写、Wiki 加厚、现有 pmem scan 生成正文、整篇覆盖。
