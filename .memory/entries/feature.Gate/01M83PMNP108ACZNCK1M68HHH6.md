---
id: 01M83PMNP108ACZNCK1M68HHH6
module: feature.Gate
entity: SpecRead
kind: feature
status: active
supersedes:
- 01M83NXHX64QDZPKYMPZBXH3KF
anchors:
- src/pmem/hooks/guard.py
- tests/hooks/test_gate.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 规格摘录带契约各节全文；已读扫描整份对话记录
verify: uv run pytest tests/hooks/test_gate.py -q -k "spec_excerpt or early_transcript
  or second_write"
applies: spec.read_before_edit 为真且闸门不是 off、本对话未跳过记忆时
aliases:
- 摘录截断
- 对话记录末尾
source:
  conversation: b0769dda-9730-42f8-84a2-6bf9080d94b7
  kind: code
---
需求来源：拦截摘录只有文件开头 800 字，会话记录只看末尾 512KB，更早的成功 Read 会被当成没读过。
必须保持：拒绝文案后面的摘录是这些节的全文：会话字段闭集、入参字段闭集、出参字段闭集、原文（须按字面抄）、失败条件、必须保持。
标题可以独占一行，也可以和第一句写在同一行，第一句仍要进摘录。
这些标题都没有时附上整份正文，不从开头截断。
规格是否已读扫描整份对话记录，不限于末尾 512KB。
还没有任何一次成功读取时，摘录给过再改仍放行；
已经记到读取之后，没读完的文件继续拦。
入口：guard.py 的 _spec_excerpt、_contract_text；payload.py 的 transcript_records。
