---
id: 01M52GBQ2Z2MPW4ZJVEB94S8XE
module: feature.Gate
entity: AutoAnchors
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_inject
- src/pmem/hooks/payload.py#_extract
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 锚点被覆盖
- anchors 丢失
- 乱码
- 转码
- updated_input
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正：闸门“Agent 自己填了 anchors 就不覆盖”在中文 Windows 上并不成立。

现象：2026-10-16 通过 MCP 写了 7 条记忆，都传了“路径#函数名”锚点，其中 5 条落盘后变成只到文件的锚点（本对话改过的文件），写入还返回“anchors 只写了文件”的提示。

根因：Cursor 按代码页 936 解码 Hook 输入，正文里的中文被损坏后 JSON 解析失败，parse_payload 退回按字段抠取（_partial），只拿到 module/entity 等字符串字段，列表型的 anchors 丢失。闸门以为 Agent 没填，用 updated_input 补上文件列表；Cursor 合并 updated_input 时把 Agent 原来的 anchors 覆盖了（正文、aliases 未受影响）。hooks.log 里可见每次 updated_input 只含 module、entity、anchors。

修复：载荷只是部分解析时不再自动补 anchors；按字段抠取时增加 draft_id，避免 Agent 自带的 draft_id 被忽略后又注入另一个。代价：这种情况下 Agent 没填 anchors 的记忆不再自动带关联代码。已用单测覆盖（构造一份含非法转义的载荷）。
