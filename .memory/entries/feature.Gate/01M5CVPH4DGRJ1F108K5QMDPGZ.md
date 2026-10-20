---
id: 01M5CVPH4DGRJ1F108K5QMDPGZ
module: feature.Gate
entity: DraftInjection
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#McpCalls._inject
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 长对话里同模块同议题同类型再写会自动覆盖早先那条，即使是另一个任务
verify: 写入后看返回的 overwritten 和 id
aliases:
- 记忆被覆盖
- draft_id 注入
- overwritten
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
风险：闸门按“本对话 + 模块 + 议题 + 类型”给 record_memory 自动注入上次的 draft_id，只要草稿还没提交就覆盖。一个对话里做了多轮任务时，后一轮的新结论会把前一轮同议题的记录整条换掉。
2026-10-20 实际踩到三次：Onboarding/Rule 的实测数据、Gate/ShellParse 第一轮结论、Retrieval/StaleCheck 功能记录都被覆盖，这些文件还没提交，版本库里取不回，只能按相关记忆重写。
识别：写入返回 overwritten: true 且 id 不是本轮刚写的。
处理：不同任务要各留一条时换议题名；已被覆盖时用同一个 draft_id 把两轮内容合并重写。MCP 上目前没有“不要覆盖”的开关。
