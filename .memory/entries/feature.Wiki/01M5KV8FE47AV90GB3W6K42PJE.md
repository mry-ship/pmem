---
id: 01M5KV8FE47AV90GB3W6K42PJE
module: feature.Wiki
entity: RebuildSpec
kind: feature
status: active
supersedes:
- 01M5KRJF0CPBSWEDSVNJ7QKC08
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 模块规格独立于 Wiki；四节，无画面的美术节写一句
applies: 使用模块规格时。Wiki 仍只浏览记忆。
aliases:
- 模块规格
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户要求的可独立重做的模块规格已单独实现（2026-10-23，Issue #16），不并进 Wiki。
必须保持：一个模块一份；
策划、美术、程序、现状四节。
无画面的模块美术节写「本模块无画面」，不因此算未完成。
有画面的把美术写进这一节。
改动的那一轮更新一次，不按时间重写，不整篇覆盖，不做记忆过期核对。
入口是 pmem spec 和 pmem-spec 技能，实现在 feature.Spec。
还没做：模块改名、合并时规格文件跟着搬。
