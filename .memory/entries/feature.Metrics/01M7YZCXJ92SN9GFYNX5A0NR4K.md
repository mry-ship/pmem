---
id: 01M7YZCXJ92SN9GFYNX5A0NR4K
module: feature.Metrics
entity: Citation
kind: conclusion
status: active
supersedes: []
anchors: []
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 字面采用率不能证明 Agent 遵守了需核实
verify: 抽查一次返回 stale 的检索；report 没有「是否先对照 check」这一列
applies: 用报表或 bench 验收 Agent 是否按需核实、替代关系和适用条件使用记忆时
aliases:
- 采用率
- 需核实遵守
- 字面重合
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
结论：pmem report 的「记忆被采用」只比回复和记忆正文的字面重合（中文 4 字加标识符，阈值 0.15）。
换说法不算，本对话刚写的记忆也不算。
它看不出 Agent 有没有先对照需核实的锚点，有没有判断 applies，也看不出有没有因为证据较弱就丢掉相关记忆。
把过期结论写进回复，采用率会反而升高。

被 supersedes 掉的记忆，现行检索不返回，Agent 读不到，也就没有「有没有正确处理替代关系」可以观察。没人填 supersedes 的旧结论仍会返回，这是写入问题；pmem map 已经会列出「更正没有写替代哪条」。

健康报告里的过期条数是库存，不是误用次数。bench 的 on/off 不加载 Hooks，只比较有没有记忆内容。

验收时效：抽查检索结果里带 stale 的对话，看后续回复有没有按 check 对照代码，再引用结论。不要为这次验收新增指标或改采用率算法。
