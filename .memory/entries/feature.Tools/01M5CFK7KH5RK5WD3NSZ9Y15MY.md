---
id: 01M5CFK7KH5RK5WD3NSZ9Y15MY
module: feature.Tools
entity: Status
kind: decision
status: active
supersedes:
- 01M59YEFJ6ZJ1S9KJYG33JVPNH
anchors:
- src/pmem/service/status.py#change_status
- src/pmem/service/base.py#fail
- src/pmem/service/base.py#returns_errors
- src/pmem/service/record.py#_record
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 失败返回带稳定错误码；restore 返回实际状态，不一致时为 mixed
aliases:
- 错误码
- error code
- 恢复后状态不对
- restore
---
决定：
1) change_status 返回实际变更后的状态：restore 回到各自归档前的状态（退回的种子回到 seed）；一批里不一致时 status 为 mixed，逐条见 statuses。
2) 失败返回带稳定错误码：fail(message, code) 输出 {ok:false, error, code}；
   RegistryError/StorageError 自带 code，returns_errors 透传。
   record 的拒绝码：content_length、secret、kind_invalid、status_invalid、entity_missing、module_deprecated、daily_cap、draft_forbidden，以及（更正：旧清单漏了）scope_invalid、supersede_cycle；
   record_rejected 事件同时记 code，health 的码表都收录了。
原因：健康报告原先靠匹配中文提示归类，改措辞就会让统计静默失效。
风险：新增拒绝分支没带 code 时健康报告归为“其他”；tests/metrics/test_health.py 有用例要求各类拒绝都带已知 code。
