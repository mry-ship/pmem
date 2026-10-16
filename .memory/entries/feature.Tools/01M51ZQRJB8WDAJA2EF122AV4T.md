---
id: 01M51ZQRJB8WDAJA2EF122AV4T
module: feature.Tools
entity: ServerMarker
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/server/app.py#_dump
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 来源标记
- 同名工具
- server字段
---
决定：MCP 服务的所有工具返回（含未接入项目时的报错）统一附加 "server": "pmem"，在 server/app.py 的 _dump 里加，service 层与命令行输出不受影响。

原因：Cursor 传给 Hook 的 MCP 工具名不带服务名，别的记忆服务的同名 search_memory 返回 ok:true 时，闸门会误以为查过了 pmem 的记忆而放行。
闸门（feature.Gate / ForeignTool）以这个标记为主要依据。

注意：不要删掉或改名这个字段；改返回包装时保留它，tests/test_server.py 有用例守着。
