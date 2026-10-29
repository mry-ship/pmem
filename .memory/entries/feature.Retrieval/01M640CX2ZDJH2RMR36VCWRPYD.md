---
id: 01M640CX2ZDJH2RMR36VCWRPYD
module: feature.Retrieval
entity: DumpRank
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#search
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 排除：祖先并入后再按 limit 截断 dump，会吃掉 inherit 名额
verify: uv run pytest tests/test_module_hierarchy.py -k ancestor_lessons or spare_own
---
排除：在祖先教训并入之后再按 limit 截断无关键词速览的结果。

子模块本模块名额已满时，上级教训是在 limit 之外另给的；并入后再 [:limit] 会把 inherit 的额外名额吃掉，上级风险不再出现。dump 只处理本模块 _spread_batches 之后、祖先并入之前。
