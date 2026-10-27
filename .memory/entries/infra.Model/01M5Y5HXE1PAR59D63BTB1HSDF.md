---
id: 01M5Y5HXE1PAR59D63BTB1HSDF
module: infra.Model
entity: Supersedes
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: MCP 传 supersedes=[] 可能清不掉替代关系，需改文件或显式重写
verify: 覆盖后 pmem search --id <新id> 看 front matter；被误伤的旧 feature 应重新出现在 search 结果
applies: 用 draft_id 改功能记录且需要去掉 supersedes 时
aliases:
- 清空 supersedes
- 误替代
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
风险：想用 draft_id 覆盖草稿并清空 supersedes 时，经 MCP record_memory 传 supersedes=[]，实测可能仍保留旧替代列表（空数组在工具层可能被当成未传）。
后果：新功能记录会误把无关旧 feature 藏起来（本轮 Templates/WriteHints/SeenDedupe 曾误伤 spec.reminder 与写作提示功能记录）。
处理：覆盖后打开记忆文件核对 supersedes 字段；要清空时直接改 front matter 去掉该键，或确认工具真的写入了空列表。
证据：2026-10-27 查漏补缺时 draft 覆盖后文件里仍有 supersedes 旧 id，visible() 仍隐藏被替代条目。
