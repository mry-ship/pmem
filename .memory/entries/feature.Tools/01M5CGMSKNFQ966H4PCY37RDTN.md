---
id: 01M5CGMSKNFQ966H4PCY37RDTN
module: feature.Tools
entity: WriteRules
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
- src/pmem/server/app.py#search_memory
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 每日上限只豁免替代本模块现行记忆；写入前看最新文件；不传 limit 时按配置
verify: uv run pytest tests/test_service.py -k "archived_entry or another_modules
  or another_process" tests/test_server.py -k limit
aliases:
- 每日上限
- daily cap
- limit 配置
- 索引节流
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户 2026-10-20 深度审查后要求修复。
必须保持：
1) 带 supersedes 的写入只有在被替代者里有本模块、未被替代、未归档的记忆时才豁免每日上限；替代已归档或别的模块的记忆照常计入上限。
2) 草稿、归档、成环、上限判断前强制刷新索引，终端刚归档的草稿不能被 MCP 用 draft_id 覆盖回现行。
3) search_memory 不传 limit（MCP 为 0，命令行不写 --limit）时按 config.yaml 的 search.limit。
入口：MemoryService.record / search。
