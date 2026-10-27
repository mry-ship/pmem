---
id: 01M5YBBS8EZ39FXA9Z76SB7SBD
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes:
- 01M5EJNBK2MZVJXYDY5HXNK1FT
anchors:
- src/pmem/hooks/mcp.py
- src/pmem/core/seen.py#claim_handoff
revision: git:3a9f17f
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: CLI --module 变量解析失败时登记 * 交接，不再完全不登记
verify: uv run pytest tests/test_quality_efficiency.py -k handoff_wildcard tests/hooks/test_gate.py
  -k variable_module
source:
  conversation: a5ba322b-9986-474a-82f5-658dd3bc9f80
---
更正：旧结论写 foreach ($m) { pmem search --module $m } 解析不出模块名就不登记，仍成立；
但单条命令里写了 --module/--path 只是值为 PowerShell 变量（如 $m）时，pre-tool 现在登记 seen.HANDOFF_ANY（*），命令行 pmem search --module <真实模块> 仍能 claim 对话 id，折叠重复全文。
仍不登记：输出丢弃、无 module/path 参数、echo 假命令。
入口：hooks/mcp.py _note_cli_calls；core/seen.py HANDOFF_ANY、claim_handoff。
与 infra.Common SeenHandoff 功能记录一致。
