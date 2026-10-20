---
id: 01M51R8M3WJ0Z9RW2QVFHTM21Z
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#_segments
- src/pmem/hooks/shell.py#cli_args
revision: git:f29e9f0
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 多行命令
- 记过了还提醒
- 误报
- 换行
---
根因：终端命令写成多行（每行一个 pmem record，或开头先有一行 `$t = $env:TEMP`）时，闸门只按 ; && || | 拆分，不按换行拆。
整条命令被当成一段，开头的 token 不是 pmem 或 uv 这类启动器，于是里面的 pmem record / pmem search 全都没有登记。

现象：一个对话里用多行命令给 feature.Storage、feature.Metrics 等模块写了记忆，记忆文件也已生成，结束时仍提醒“本轮修改了 feature.Storage、feature.Metrics，但还没有写研发记忆”。
会话状态的 cli_recorded 里没有这两个模块，events.jsonl 里也没有对应的 record_call。
同样写法的 pmem search 不算“已查过”，会被多拦一次；
写文件目标也可能漏识别。

处理：拆分时把换行也当分隔符；行尾是 PowerShell 续行符（`）或 shell 续行符（\）的，先把下一行接回来再拆。排查“记过了还提醒”时，先看那条命令是不是多行。
