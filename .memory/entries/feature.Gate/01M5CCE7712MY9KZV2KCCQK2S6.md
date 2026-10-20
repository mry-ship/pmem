---
id: 01M5CCE7712MY9KZV2KCCQK2S6
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#_pop_cli_pending
- src/pmem/hooks/mcp.py#_confirm_cli_calls
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 终端检索前后命令文本不同时按模块名认领挂起，并行检索不再被拦
verify: pytest tests/hooks/test_gate.py -k cli_search_matched_by_module or parallel_cli_searches
aliases:
- 查过还被拦
- 并行检索
- 乱码
---
结论：终端 pmem search 执行完仍被闸门拦“没查过”，根因是挂起条目按命令文本的键认领，而 preToolUse 和 postToolUse 拿到的命令文本可能不同。
现象：同一对话里并行跑几条 pmem search --module X "中文关键词"，或用 foreach 循环查多个模块，之后编辑这些模块的文件仍被拒绝。
原因：检索词里的中文在两次 Hook 载荷里转码不同，_command_key 算出的键对不上；原兜底只在“只剩一条挂起”时认领，并行时有多条挂起，全部认领失败、留在 cli_pending 里。
修复：键对不上时按命令里的模块名（ASCII，不受转码影响）找挂起条目，取最近一条；认不出模块时才退回“只剩一条才认领”，并行的 ls 这类不含 pmem 调用的命令照旧不能拿走别人的挂起。
仍然不行的写法：foreach ($m in ...) { pmem search --module $m }，Hook 解析不出变量里的模块名，不会登记；要一条命令写一个模块名。
