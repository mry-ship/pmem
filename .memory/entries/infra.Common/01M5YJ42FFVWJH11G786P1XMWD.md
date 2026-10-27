---
id: 01M5YJ42FFVWJH11G786P1XMWD
module: infra.Common
entity: SeenHandoff
kind: correction
status: active
supersedes:
- 01M5Y5A4P1EQE643AJ5K0481N6
anchors:
- src/pmem/core/seen.py#looks_like_shell_var
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: '* 交接只认 Shell 变量占位，不认解析失败的模块名'
verify: uv run pytest tests/test_quality_efficiency.py -k "handoff or looks_like_shell
  or unresolved_module"
applies: 解释对话内重复偏高或改 cli 交接时
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
更正：有 --module/--path 但 resolve 失败就登记 *，会把拼错模块名当成通配。
现在：looks_like_shell_var 只认 $m / ${m} / $env:X / %M%；拼错名和未登记路径登记空列表。claim_handoff 对指定模块仍认该模块或 *；空列表只给全局检索。
仍成立：认领后不删交接、120 秒、最多 8 条。
