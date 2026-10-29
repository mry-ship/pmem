---
id: 01M640J8PC2W4NZ0CAMNPWWHMJ
module: feature.Curation
entity: PitfallKindHint
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/quality.py#content_hints
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 结论或决定开头像排除项时提示改用 exclusion，只提示不拦截
verify: uv run pytest tests/core/test_quality.py -k exclusion_shaped
---
用户要求：合并和统计不要把防错类收成普通结论。

必须保持：kind 为 conclusion 或 decision 时，去掉开头的“决定/结论”标签后，正文开头像“排除/不要/禁止”的，提示改用 exclusion；
只提示不拦截。
已是 exclusion/risk/correction 的不提示。

适用：写入质量检查；不改变硬拦截规则。

入口：src/pmem/core/quality.py#content_hints
