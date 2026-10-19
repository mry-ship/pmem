---
id: 01M52G7A71H7RJFBEYNRCY44X1
module: feature.Tools
entity: Status
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/status.py#change_status
- src/pmem/service/record.py#record
- src/pmem/service/record.py#_record
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 归档
- 种子记忆
- seed
- 转正
- 被拒绝的写入
- record_rejected
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：记忆状态的变更集中在 MemoryService.change_status，只允许四种动作：archive（active/seed/draft → archived）、restore（archived → active）、accept（seed → active）、reject（seed → archived）。只改 YAML 头的 status，正文、id、替代关系不变；状态不符的条目放进 skipped 返回，不报错也不改。这些动作只走命令行（pmem archive / pmem seed），不暴露为 MCP 工具，AI 不能自行归档。

record 新增 status 参数（只接受 active/seed/draft，命令行 --seed），用 draft_id 覆盖时没传 status 则沿用草稿原状态，避免种子草稿被覆盖成正式记忆。

写入被拒绝（字数、敏感信息、每日上限、草稿覆盖、模块名等）时记一条本机事件 record_rejected（模块、议题、错误前 200 字），供 pmem health 统计；原先拒绝不留任何记录。实现上 record 变成薄包装，原逻辑在 _record。
