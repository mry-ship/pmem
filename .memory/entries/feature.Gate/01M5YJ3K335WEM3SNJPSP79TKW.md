---
id: 01M5YJ3K335WEM3SNJPSP79TKW
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes:
- 01M5YBBS8EZ39FXA9Z76SB7SBD
anchors:
- src/pmem/hooks/mcp.py#_note_cli_calls
- src/pmem/core/seen.py#looks_like_shell_var
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 只有 $m 这类变量才登记 * 交接；拼错模块名不当通配
verify: uv run pytest tests/test_quality_efficiency.py -k "handoff or looks_like_shell
  or unresolved_module"
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
更正：解析不出模块时一律登记 * 过宽。拼错或不存在的模块名（如 feature.Hooks）、未登记路径也会变成通配，120 秒内任意模块的 CLI 检索都可能认走这个对话、折叠正文。
现在：仅当 --module/--path 的值像 Shell 变量（$m、${m}、$env:FOO、%M%）时才登记 seen.HANDOFF_ANY；其余解析失败登记空列表，只给全局检索认领。闸门放行仍须字面模块名。
入口：core/seen.py looks_like_shell_var；hooks/mcp.py _note_cli_calls。
