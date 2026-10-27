---
id: 01M5CAVRWPET8KQNB0ZSX1DGMA
module: feature.Curation
entity: WriteHints
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/quality.py#content_hints
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 功能记录的写作提示改为检查需求来源和必须保持的行为
aliases:
- 写作提示
- 需求来源
verified: '2026-10-27'
verified_at: '2026-10-27T15:52:36.858+08:00'
---
用户要求（2026-10-19）：功能记录要写成“谁要的、哪些行为不能改掉”，而不是变更日志。
必须保持：写作提示对 feature / plan 不再查“缺原因、像变更记录”，改为没写需求来源或必须保持的行为时提示一次（core/quality.py 的 _REQUIREMENT 词表）。
TileMatch 的 quality.py 副本若要同步，需要连同 RECORD_KINDS 分支一起搬。
