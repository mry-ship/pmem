---
id: 01M7WT971T4NY7EJJKWJ0TQJPM
module: feature.Tools
entity: EnforcedBy
kind: feature
status: active
supersedes:
- 01M7WFT4065KE227PTJHG77JZA
anchors:
- src/pmem/server/app.py#record_memory
- src/pmem/service/search.py
- src/pmem/cli/brief.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: enforced_by 写入/检索；摘要双态标拦截或规则需核实
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 改 record/search 的 enforced_by 参数、hint 或 MCP 文档时
---
需求来源：深检复核——MCP/brief 若仍只写「已由规则拦截」，规则已删或改过时 Agent 会误当已拦住。

必须保持：
- record_memory / pmem record 可写 enforced_by；覆盖草稿时没传沿用、传空清空；路径规范化与密钥检查与 anchors 共用。
- 检索行带 enforced_by，并给 enforced_hint：规则文件与符号仍在时标「已由规则拦截」并靠后排；规则缺失/改过/找不到符号时改标「规则需核实」，勿当已拦住。
- brief 与 MCP record_memory 文档口径与上述双态一致。

入口：service/record.py、service/search.py、server/app.py、cli/brief.py、cli/main.py。
