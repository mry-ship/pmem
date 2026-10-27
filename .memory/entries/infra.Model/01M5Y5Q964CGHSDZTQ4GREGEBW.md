---
id: 01M5Y5Q964CGHSDZTQ4GREGEBW
module: infra.Model
entity: DraftId
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 排除：用别条记忆的 draft_id 覆盖来“改写”另一条
verify: 覆盖前核对 draft_id 与目标文件 id、kind 一致
applies: record_memory 带 draft_id 时
aliases:
- draft_id 覆盖错条
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
排除：把 conclusion 的 id 当 draft_id 去写 exclusion（或反过来），会整条覆盖原 kind/正文，旧结论丢失。
证据：二次查漏时误把 AnalysisWrap 结论 01M5Y51P9WPSA81REYAD5RX2E6 用 draft_id 写成 exclusion，只能手改文件恢复。
处理：新类型/新结论一律不传 draft_id；draft_id 只用于覆盖“同一条未提交草稿”的同 kind 修订。
