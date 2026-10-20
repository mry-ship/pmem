---
id: 01M5CJX3ZZSH787WCB8AS5WBCQ
module: feature.Gate
entity: Encoding
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#_inject
- src/pmem/hooks/payload.py#parse_payload
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 中文 MCP 检索约六成用乱码查询：Hook 把损坏的参数经 updated_input 回传
scope: project
verify: 在 Cursor 里用中文 query 调 search_memory，看 events.jsonl 最后一条 source=mcp 的 search
  事件 query 是否为正常中文；单测 uv run pytest tests/hooks/test_gate.py -k only_added
aliases:
- 乱码
- 转码
- GBK
- 代码页 936
- 查询词损坏
- updated_input
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
根因：Cursor 在中文 Windows 上按代码页 936 转码 Hook 输入。
parse_payload 在原样和 GBK 回转都能解析时取“痕迹少”的一份，乱码本身常没有替换符和私有区字符，于是选中了乱码版本；
回转时又会因截断字节丢字。
闸门对 search_memory 注入 source_conversation 时把整份参数放进 updated_input，Cursor 按字段合并，Agent 原本正确的 query 被乱码覆盖，记忆服务拿乱码检索。
证据（2026-10-20，本机 events.jsonl 里服务端记录的 source=mcp 检索）：含中文的 MCP 检索 10-16 有 14/25 是乱码，10-19 有 38/71，10-20 有 29/45；
hooks.log 里 updated_input 的 query 同样是乱码。
30 次能还原的乱码检索里，只有 12 次前 5 条结果和用正确查询词时相同，纯中文查询最差只有 1/5 重合；
另有约 36 次截断到无法还原。
终端 pmem search 不经 updated_input，不受影响。
记忆正文未受污染：record 载荷多数解析失败，只抠出部分字段，正文没有回传。
修复后实测：updated_input 只含 source_conversation，服务端收到的模块和中文 query 正确，并带上了对话 id，证明 Cursor 是按字段合并、不是整体替换。
影响：修复前的检索评测题（真实检索记录）里，部分“当时的答案”来自乱码检索结果。
