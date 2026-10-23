---
id: 01M5KRJTP6WQYWKZZ30DYKXJST
module: feature.Wiki
entity: RebuildSpec
kind: exclusion
status: active
supersedes: []
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: Wiki 加厚、现有 scan、整篇覆盖，都写不出可独立重做的模块规格
applies: 做可独立重做模块的规格时，想用 Wiki、现有 pmem scan，或像 Wiki 一样整篇重生成。
aliases:
- Wiki不够
- 整篇覆盖
- pmem scan 生成规格
- 记忆汇编
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
排除两条路：
1) 把 Wiki 加厚、去掉需核实、或改成定时重生成，当成可以单独拿走、照着把模块重做出来的文档。Wiki 只按议题堆现行记忆并附演化图，拷走仍是结论汇编。
2) 用现有 pmem scan 按模块生成这份规格，以及模块变更后像 Wiki 一样整篇覆盖。
   scan/lite.py 的 run_scan 只输出目录概览和提交热度，不读代码行为。
   Wiki 能整篇重写，是因为它每句话都来自记忆；
   这份规格本身是记录，整篇覆盖会把代码里看不出的策划意图和美术说明冲掉。
处理：独立目录、进版本库，不要塞进 Wiki 页面。首次由 Agent 按模块读代码写底稿；以后只更新变更波及的程序与现状段落，策划段和美术段保留。没有画面的美术节写「本模块无画面」。
