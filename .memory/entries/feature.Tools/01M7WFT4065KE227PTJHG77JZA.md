---
id: 01M7WFT4065KE227PTJHG77JZA
module: feature.Tools
entity: EnforcedBy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
- src/pmem/server/app.py#record_memory
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 写入与检索支持 enforced_by；覆盖沿用；brief 标已由规则拦截
verify: uv run pytest tests/core/test_entry.py -k enforced_by
applies: 改 record/search 的 enforced_by 参数或展示时
---
需求来源：v0.7 规则化，写入侧要能声明已由规则保障。
必须保持：record_memory / pmem record --enforced-by 可写入；
覆盖草稿时没传沿用原值、传空清空；
路径规范化与密钥检查与 anchors 共用；
检索行带 enforced_by，并给 enforced_hint；
brief 标「已由规则拦截」。
适用：改 record/search 的 enforced_by 参数或展示时。
入口：service/record.py、server/app.py、cli/main.py、service/search.py、cli/brief.py。
