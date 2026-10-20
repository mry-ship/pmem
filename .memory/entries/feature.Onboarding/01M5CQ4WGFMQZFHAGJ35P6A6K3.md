---
id: 01M5CQ4WGFMQZFHAGJ35P6A6K3
module: feature.Onboarding
entity: Rule
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#RULE_BODY
- src/pmem/server/app.py#build_server
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 规则只说何时查写；字段写法归 record_memory 说明，结果字段含义归检索提示
verify: uv run pytest tests/test_feature_records.py -k trimmed_rule
aliases:
- 规则精简
- 上下文占用
- token 开销
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
决定（2026-10-20，用户要求在功能不变的前提下精简规则和提示）：同一件事只在需要它的地方说一次。
- 规则 pmem.mdc 只管“什么时候做”：何时查、何时写、回复末行的检查结果、[pmem] 提醒直接处理、跳过记忆、工具不可用时改用终端。
- 字段怎么填只写在 record_memory 的工具说明（终端见 pmem record --help）；结果字段（stale、seen、features、applies）的含义只在检索结果的 *_hint 里说，每个对话一次。
- 没动的：拦截时的拒绝消息（Cursor 只把它交给助手）、[pmem] 前缀、用户要求的回复末行。
实测：精简前每次请求固定带规则 2469 字和 5 个工具说明及参数结构约 4200 字（record_memory 约 2100）；
读码摘要每次 600～900 字；
检索返回每次约 4900 字，其中记忆正文约 2300、固定提示 316。
精简后规则约 1280 字，工具说明文字合计 1315 字。
真正占大头的是记忆正文，不该缩。
风险：只走终端 pmem record 的助手看不到工具说明，靠 --help 和写入返回的 hints；
以后加字段写法不要再写回规则。
效果是否真的不变要用 pmem report / health 对比前后一周：改前没查被拦次数、功能记录覆盖率、被拒写入、结束提醒次数。
