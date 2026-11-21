---
id: 01M7Z2N09N4MA50AD4TRMSS7ZV
module: feature.Onboarding
entity: P1Sample
kind: conclusion
status: active
supersedes: []
anchors: []
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: P1 抽查未见按过期结论改代码，不改提示也不进 P3
verify: 重看这几段对话：5500e8d7、dd30165a、8d84bffd、22cdc6c7；事件日志里 confirm 仍是原有 3 次
applies: 想因需核实误用去改检索提示或进入 P3 时
aliases:
- 需核实抽查
- P1
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
结论：2026-11-21 按冻结路线做了 P1 抽查，没有发现按过期结论改代码。
编码样本覆盖规格默认值、最小方案、发版和 MCP root：检索到锚点已过期的记忆后，都先打开了对应源码再下结论。
其中一次明确写了锚点标了需核实、这次不确认。
问答样本覆盖规格默认值和厄尔尼诺简报：前者按文件行号报告当前代码，后者用的是另一个项目的记忆并读了那边的代码。

没有人调用 confirm_memory。本路线图对话复述过一条标了需核实的耗时数字，没打开 anchors.py，也没因此改代码。

据此停：不改检索提示，不加机制，不进入 P3。对话记录里没有工具返回原文，这次是看检索之后有没有打开锚点文件，不是新指标。当前 444/683 条过期是库存，不是误用次数。
