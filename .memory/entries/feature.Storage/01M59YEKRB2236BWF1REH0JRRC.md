---
id: 01M59YEKRB2236BWF1REH0JRRC
module: feature.Storage
entity: DraftId
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/storage/files.py#StorageError
- src/pmem/storage/files.py#_check_draft
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 错误码
- 草稿覆盖被拒
- error code
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:16.631+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：StorageError 增加 code 属性。draft_id 不合法、对应记忆不存在、作者不同、跨模块、已提交到版本库这五种覆盖拒绝统一为 draft_forbidden（服务层“已归档不能覆盖”同码），其余默认 storage。
原因：健康报告原先靠“不能覆盖”“不能改到”等字样归类，“不是有效的记忆 id”“不存在”两类原本会落进“其他”。
影响：拒绝条件和提示文字不变，只在返回里多 code。
