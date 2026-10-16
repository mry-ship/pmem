---
id: 01M51ZH2XRQHVQV6HB00BMAXVS
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes:
- 01M4X7MV5T0RF0ZQYDDGJ1J768
- 01M4Z5DGNT04KV06074JS5CYY6
- 01M51R8M3WJ0Z9RW2QVFHTM21Z
anchors:
- src/pmem/hooks/shell.py#cli_args
- src/pmem/hooks/shell.py#_statements
- src/pmem/hooks/gate.py#_note_cli_calls
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 记过了还提醒
- 误报
- 多行命令
- 启动器
---
结论：终端命令里的 pmem search / graph / record 与对应 MCP 工具等价，闸门必须逐个认出并登记，否则会误报“还没写研发记忆”、查过了还被拦。踩过三类漏认，均已修复：

1. 一条命令用 ; && || | 串了多个 pmem 调用时只认第一个。现在拆段后逐个登记。
2. `uv run --extra embed pmem record ...` 这类 pmem 前面带参数的写法认不出。
   现在以 uv / uvx / pipx / python 等启动器开头时，在后面的参数里找 `pmem <子命令>`；
   `echo pmem search` 这类非启动器开头的不算。
3. 多行命令（每行一个 pmem record，或开头先有一行 `$t = $env:TEMP`）被当成一段。现在换行也是分隔符，行尾是续行符（PowerShell 的 ` 或 shell 的 \）时先接回去再拆。

search、graph 的输出被丢弃（> $null、| Out-Null、重定向到文件）时不算查过。

排查“记过了还提醒”：先看会话状态（缓存目录 sessions/<对话id>.json）里的 cli_recorded，再用 cli_args 解析当时的原始命令，重点看是否多行、是否带启动器参数、调用前是否发生过 preCompact（压缩清空 searched，不清空 cli_recorded）。
合并自 3 条记忆。
