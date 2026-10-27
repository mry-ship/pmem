---
id: 01M5Y1RGSN27GQY51C2YAZVSEE
module: feature.Spec
entity: EmptyMarker
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#status_of
- src/pmem/generate/spec.py#gap_label
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 空标记与 design-gap 只认整行；正文反引号提到字面量不算未完成
verify: pytest tests/test_spec.py -k mentioning_empty；本仓库 feature.Spec 为已有规格
applies: 规格正文需要提到空标记原文，或运行 pmem spec --check 时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：feature.Spec 自述里写了 `<!-- spec:empty -->` 被误判为首稿未完成。
必须保持：status_of / gap_label 用整行正则匹配 EMPTY 与 DESIGN_GAP；反引号或句子中的字面量不触发未完成/留空。
适用：判断规格完成度与总目录留空列时。
入口：generate/spec.py 的 _EMPTY_LINE、_DESIGN_GAP_LINE。
