---
id: 01M83R5GWG3NCVCR57JK83SQTZ
module: feature.Gate
entity: ReadPairing
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/guard.py#_successful_read_args
revision: git:223a61d
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 同一 Read 的多个结果里，有一次成功就算已读
verify: 构造同一 id 先 is_error 再成功的 tool_result，_successful_read_args 仍返回该 Read 的 input
applies: 用对话记录判断某次 Read 是否已经成功读到规格时
aliases:
- 成功结果覆盖失败
- Read 异常结果
source:
  conversation: e0ffd8af-3de7-48fb-8ac0-0d832c508a60
  kind: code
---
现象：_successful_read_args 对同一工具 id 的多个 tool_result，把失败标志做成相与：只有全部结果都失败才不算已读。先失败后成功，或先成功后失败，都会把这次 Read 当成已读。

证据：用同一 id 配一条 is_error 和一条成功内容，两种顺序都返回了该 Read 的 input。注释写的是「结果标了失败，都不算」，实现却是有一次成功就盖过失败。

影响：同一次 Read 的异常结果可能被另一条成功结果洗成已读。tests/hooks/test_gate.py 只覆盖单独一次 is_error，没有同一 id 的成败混合。
SpecRead 当天已有 5 条，这条因此写在 ReadPairing，不替代「摘录给契约全文、已读扫描整份对话」那条功能记录。
