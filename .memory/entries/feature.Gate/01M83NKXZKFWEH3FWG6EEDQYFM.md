---
id: 01M83NKXZKFWEH3FWG6EEDQYFM
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes:
- 01M5YJ3K335WEM3SNJPSP79TKW
- 01M6R9WC3RH7DRARWJ2EW0J3GZ
anchors:
- src/pmem/hooks/mcp.py#_note_cli_calls
- src/pmem/core/seen.py#looks_like_shell_var
- src/pmem/hooks/shell/targets.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 变量才登记通配；锚点改指 shell/ 包
aliases:
- 通配
- shell.py
source:
  kind: document
---
更正：
1) 解析不出模块时不要一律登记 *。
   只有 --module/--path 的值像 Shell 变量（$m、${m}、$env:FOO、%M%）才登记通配；
   拼错的模块名或未登记路径登记空列表，只给全局检索认领。
   闸门放行仍须字面模块名。
   否则 120 秒内任意模块的 CLI 检索都可能认走这个对话。
2) shell.py 已拆成 shell/ 包。锚点要写 shell/targets.py、shell/lexer.py 等真实文件，不要再指已删除的 shell.py，否则整批报「已不存在」。

合并自 2 条更正。
