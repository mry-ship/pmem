---
id: 01M5M94VD6HWVAYD7V9E0X4T5S
module: feature.Spec
entity: EmptyMarker
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py
- src/pmem/generate/templates.py
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 去掉空标记不等于能重做；反推不过仍要补
verify: 对照 .memory/specs 里曾只有增量的模块：补全后应能单独讲清入口和词表
applies: 判断模块规格是否写全、或 --check 已通过时
aliases:
- 空标记
- 首稿未完成
- 已有规格
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
排除：用「程序和现状没有空标记」当作规格已经写全。
证据：本仓库曾有 6 个模块被标成已有规格，正文却只写了规格功能那一轮的增量（例如闸门只写了规格提醒、配置模块写「默认提醒打开」甚至与现行缺省相反），拿这四份无法重做该模块。
处理：--check 仍只看空标记，这是命令行的确定性底线；写正文的人还要用反推验收。已经去掉空标记但缺入口、闭集词表、所有权、决定表或一轮例子的，缺哪一类补哪一类。
没选：把 --check 改成读懂正文是否可重做（命令行做不到判断性检查）。
