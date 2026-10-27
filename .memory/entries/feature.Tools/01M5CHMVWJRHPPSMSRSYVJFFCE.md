---
id: 01M5CHMVWJRHPPSMSRSYVJFFCE
module: feature.Tools
entity: WriteRules
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/service/record.py
- src/pmem/server/app.py#search_memory
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 写入规则曾看不到 10 秒内别的进程的写入，且替代归档或他模块记忆可绕过每日上限
verify: uv run pytest tests/test_service.py -k "cap or another_process" tests/test_server.py
  -k limit tests/test_cli_flow.py -k limit
aliases:
- 每日上限
- daily cap
- search.limit
- 节流
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
根因一：MemoryIndex 有 10 秒刷新节流，写入前的草稿、归档、循环替代、每日上限检查用的是旧索引；另一个进程（终端 pmem record、另一个 MCP 实例）刚写的记忆看不到，规则判断失真。写入前改为强制刷新。
根因二：“替代现行记忆不占每日上限”原先只看 supersedes 是否命中，替代已归档的记忆、或替代别的模块的记忆也能免上限，等于可以无限写。
现只在替代本模块现行可见的记忆时免上限。
跨模块 supersedes 本身仍允许，只是不再免上限。
根因三：search_memory 的 limit 参数在 MCP 和 CLI 上都有写死的默认值，config.yaml 的 search.limit 从未生效；改为不传时读配置。
