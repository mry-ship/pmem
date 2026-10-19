---
id: 01M59J9C0FFHN1CMZ9PD2M4PB5
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#_record_content
- src/pmem/cli/main.py#main
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- stdin 乱码
- GBK
- 管道写入
- 命令行参数
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：命令行入口新增两个用法：
- pmem migrate move <id>... --to <模块>
- pmem anchors --rename 旧=新（可写多次，配 --apply）
具体逻辑在 catalog/migrate.py 和 cli/anchors_cmd.py，main.py 只负责解析和分发。
修复：pmem record 从 stdin 读正文时，原先用 sys.stdin 按系统编码（中文 Windows 为 GBK）解码，Agent 管道传来的 UTF-8 中文变成乱码甚至报 UnicodeDecodeError；
现在读字节按 utf-8-sig 解码，也兼容 PowerShell 带的 BOM。
