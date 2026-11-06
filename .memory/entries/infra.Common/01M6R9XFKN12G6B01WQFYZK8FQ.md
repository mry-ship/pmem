---
id: 01M6R9XFKN12G6B01WQFYZK8FQ
module: infra.Common
entity: McpEnable
kind: correction
status: active
supersedes:
- 01M6R7NC7CQRSAD8E6QJTWKEX6
anchors:
- src/pmem/generate/mcp_enable.py#_claude_project_keys
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: Claude 启用已改精确路径匹配，用户配置已原子写
---
已修：_claude_project_keys 改为 Path(key).resolve()==root.resolve() 精确匹配，同名不同路径不再一并启用；
~/.claude.json 与 ~/.codex/config.toml 改 write_atomic。
见功能记录 01M6R9K7QWYGSP6FXXM6GXH5WQ。
