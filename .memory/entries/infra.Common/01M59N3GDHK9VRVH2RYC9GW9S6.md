---
id: 01M59N3GDHK9VRVH2RYC9GW9S6
module: infra.Common
entity: Docs
kind: decision
status: active
supersedes: []
anchors:
- docs/images/pmem-flow.svg
- docs/pmem-guide.html
- README.md
revision: git:0f81ce5
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 流程图
- 时序图
- pmem-flow
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：README 和手册里的「一次对话流程」图（docs/images/pmem-flow.svg）按五个环节分色带，左侧写环节名：接手（读代码附摘要）、①改前查、改代码（闸门校验）、②写结论、③提交共享。
蓝底是 Agent 主动三步，橙底是闸门介入，绿底是提交后队友可见；
底部有图例。
手册「日常使用」也嵌入同一张图。
原因：旧图只有箭头旁的小圆点编号，环节边界看不清，闸门介入和主动步骤混在一起。
