---
id: 01M5EJNBK2MZVJXYDY5HXNK1FT
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes:
- 01M51ZH2XRQHVQV6HB00BMAXVS
- 01M5CCE7712MY9KZV2KCCQK2S6
anchors:
- src/pmem/hooks/shell.py#cli_args
- src/pmem/hooks/shell.py#_statements
- src/pmem/hooks/mcp.py#_note_cli_calls
- src/pmem/hooks/mcp.py#_pop_cli_pending
- src/pmem/hooks/mcp.py#_confirm_cli_calls
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 终端 pmem search/record 须执行后看到输出才登记；模块名要写字面值
aliases:
- 记过了还提醒
- 查了还拦
---
结论：终端里的 pmem search / graph / record 与对应 MCP 工具等价，闸门必须逐个认出并登记，否则会误报“还没写研发记忆”、查过了还被拦（“记过了还提醒”“查了还拦”）。

现行规则：
- 一条命令里多个 pmem 调用（; && || | 或多行，行尾续行符 ` 或 \ 先接回）拆段后逐个登记。
- 以 uv / uvx / pipx / python 等启动器开头时在后面的参数里找 pmem <子命令>（如 uv run --extra embed pmem record）；
  & pmem、& "C:\...\pmem.exe" 也认；
  echo pmem search 不算。
- search、graph 执行后输出里看得到模块才登记，输出被丢弃（> $null、| Out-Null、重定向到文件）不算查过。
- record 也是挂起，执行后输出里同时看到模块名和 draft_id 才登记，否则记 record_call_failed；载荷无输出字段时照旧登记。注入 draft_id 前先看草稿是否已提交。
- 挂起条目先按命令文本的键认领；
  preToolUse 和 postToolUse 里中文检索词转码可能不同、键对不上时，按命令里的模块名（ASCII）取最近一条；
  认不出模块时只在“只剩一条挂起”且本命令也含 pmem 调用时兜底，并行的 ls 不能拿走别人的挂起。

仍然不行：foreach ($m in ...) { pmem search --module $m } 解析不出变量里的模块名，不登记；要一条命令写一个字面模块名。
状态文件：损坏时按默认值重建，PermissionError 重试 5 次，Hook 只输出一次 JSON，出错会提醒用户。
风险：record 的成功判断依赖输出含 draft_id，改 record 输出格式要同步。
排查：看缓存目录 sessions/<对话id>.json 的 cli_recorded、cli_pending，用 cli_args 解析原始命令，看是否多行、带启动器参数、调用前是否发生过 preCompact（压缩清空 searched，不清空 cli_recorded）。
合并自 3 条记忆。
