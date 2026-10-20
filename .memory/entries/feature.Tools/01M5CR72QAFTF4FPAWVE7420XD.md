---
id: 01M5CR72QAFTF4FPAWVE7420XD
module: feature.Tools
entity: WriteRules
kind: feature
status: active
supersedes:
- 01M5CGMSKNFQ966H4PCY37RDTN
anchors:
- src/pmem/service/record.py#_record
- src/pmem/service/status.py#confirm
- src/pmem/service/status.py#change_status
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 草稿覆盖只在同模块同议题当天才免上限；summary/entity 有硬上限；锚点查密钥
verify: uv run pytest tests/test_service.py -k "daily_cap or overlong or anchors or
  unknown_front_matter or another_process"
aliases:
- 每日上限
- daily cap
- 草稿覆盖
- entity_invalid
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，复查发现写入规则还有可绕过的地方。
必须保持：
1) 带 draft_id 覆盖只有在被覆盖的是本模块、同议题（不分大小写）、当天写的草稿时才不计入每日上限；换了议题或覆盖前几天的草稿照常计数。原先任何 draft_id 都免上限，可以借一条草稿把别的议题无限写下去。
2) 带 supersedes 的写入只有在被替代者里有本模块、未被替代、未归档的记忆时才豁免每日上限。
3) summary 超过 200 字拒绝（code=content_length），60 字以内仍只是建议；entity 必须单行且不超过 60 字，否则 code=entity_invalid（health 的被拒写入已归类）。
4) anchors 和 entity、aliases、summary、verify、applies 一样做密钥检测。
5) 覆盖草稿时保留旧文件 YAML 头里不认识的字段（较新版本写的字段不丢）。
6) confirm、归档/恢复等状态变更遇到读不出或写不进的记忆文件，逐条列在 invalid（id 和原因），其余照常处理，ok 反映是否全部成功；revert 出错返回错误码不抛异常。
7) 草稿、归档、成环、上限判断前强制刷新索引；search_memory 不传 limit 时按 config.yaml 的 search.limit。
入口：MemoryService.record / confirm / change_status / revert。
