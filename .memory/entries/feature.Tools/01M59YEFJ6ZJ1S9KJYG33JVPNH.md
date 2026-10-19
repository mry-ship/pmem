---
id: 01M59YEFJ6ZJ1S9KJYG33JVPNH
module: feature.Tools
entity: Status
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/status.py#change_status
- src/pmem/service/base.py#fail
- src/pmem/service/base.py#returns_errors
- src/pmem/service/record.py#record
- src/pmem/service/record.py#_invalid_content
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 错误码
- error code
- 恢复后状态不对
- restore
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：
1) change_status 返回的 status 改为实际变更后的状态。
   restore 回到各自归档前的状态（退回的种子回到 seed），原先返回值恒为 active，与文件不符；
   一批里状态不一致时 status 为 mixed，逐条见 statuses。
2) 失败返回带稳定错误码：fail(message, code) 输出 {ok:false, error, code}；
   RegistryError/StorageError 自带 code，returns_errors 透传。
   record 的拒绝码：content_length、secret、kind_invalid、status_invalid、entity_missing、module_deprecated、daily_cap、draft_forbidden；
   record_rejected 事件同时记 code。
原因：健康报告原先靠匹配中文提示归类，改措辞就会让统计静默失效（issue #11）。
影响：MCP 和命令行的失败返回多一个 code 字段，error 文字不变。
风险：新增拒绝分支没带 code 时，健康报告退回按文字匹配或归为“其他”；tests/metrics/test_health.py 有用例要求各类拒绝都带已知 code。
