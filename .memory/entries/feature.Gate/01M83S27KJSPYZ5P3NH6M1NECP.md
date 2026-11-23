---
id: 01M83S27KJSPYZ5P3NH6M1NECP
module: feature.Gate
entity: SpecRead
kind: feature
status: active
supersedes:
- 01M83R5GWG3NCVCR57JK83SQTZ
anchors:
- src/pmem/hooks/guard.py#_contract_text
- src/pmem/hooks/guard.py#_successful_read_args
revision: git:223a61d
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 未知栏目结束契约节；同一 Read 有失败就不算已读
verify: uv run pytest tests/hooks/test_gate.py -q -k "unknown_heading or colon_ended
  or mixed_success or spec_excerpt"
applies: spec.read_before_edit 为真且闸门不是 off、本对话未跳过记忆时
aliases:
- 契约串读
- Read 异常结果
source:
  conversation: e0ffd8af-3de7-48fb-8ac0-0d832c508a60
  kind: code
---
需求来源：契约摘录会把后面的栏目混进上一节；同一条 Read 的失败结果会被另一条成功结果洗成已读。
必须保持：摘录仍是会话字段闭集、入参字段闭集、出参字段闭集、原文（须按字面抄）、失败条件、必须保持的全文。标题可以和第一句写在同一行，第一句仍进摘录。这些标题都没有时仍附上整份正文。
Markdown 标题，以及骨架里的其他栏目，结束当前契约节，后文不归入上一节。原文里单独成行、以冒号结尾的句子不是新栏目。
同一条 Read 的每条 tool_result 都未标失败才算已读；有一条失败就不算。没有配对结果也不算。
入口：guard.py 的 _contract_text、_successful_read_args。
