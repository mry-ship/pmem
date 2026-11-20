---
id: 01M7WTANF0JTSNTTNPGWW665BM
module: infra.Model
entity: EnforcedBy
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#enforced_mark
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 排除：规则失效时仍标已由规则拦截
verify: uv run pytest tests/core/test_entry.py -k enforced_by; pytest tests/test_wiki.py
  -k needs_check
applies: 改 enforced_mark 或摘要/Wiki/brief 规则标注时
---
排除：规则文件缺失、改过或找不到符号时，标题仍标「已由规则拦截」。

原因：AI 会当成坑已被工程规则拦住，跳过人工核对；实际规则已失效。应改标「规则需核实」，并保留关联代码的需核实信息。
