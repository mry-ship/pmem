---
id: 01M7X5YZXNTPK81EDT2ZTP69XW
module: feature.Retrieval
entity: CredibilityRank
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#search
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 来源和核对不参与检索排序，也不压成可信度分数
verify: 带关键词的检索顺序与现有相关度排序一致；来源或 verified 不改变名次
applies: 实现记忆证据、适用条件、有效时间，或讨论正确记忆召回时
aliases:
- 可信度
- 重排
- 来源种类
---
排除：把来源种类、核对日期、适用条件或有效时间压成一个可信度分数，再用它重排或过滤检索结果。

来源（human、code、test、conversation、document、inference）只说明证据从哪来。
核对（verified）只说明何时对照过锚点。
when 和 applies 只说明前提。
valid_from 只说明何时生效。
四者分开，也不要互相推导：人工来源、测试通过、代码里找得到，都不等于设计正确，也不等于所有环境成立，更不能据此自动写成已核对。

已经不适用的沿用现有规则排除：被替代的不返回；查询带了 when 且明确冲突的排除，没写 when 的照常返回。过期、来源不明、未经核对的保留并在结果里标记。有关键词时名额内仍按相关度排序，可信度高但不相关的记忆不挤占名额。

不替代已有排除项：when 冲突不是降权后仍返回；有关键词时不把防错类提前；不设相关度阈值。
