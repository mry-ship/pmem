---
id: 01M7WKR5R8ASY5BSHQR566KWJB
module: feature.Wiki
entity: WhenFacets
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#enforced_mark
- src/pmem/generate/wiki.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: Wiki/摘要展示 when；规则失效标「规则需核实」
verify: uv run pytest tests/test_wiki.py -k when_and_enforced
applies: 改 Wiki 条目渲染、when 或 enforced_by 展示时
---
需求来源：v0.7 §3.2 / §3.3；设计要求检索、读码摘要、Wiki 标题后标「已由规则拦截」，并展示结构化 when；再修规则失效时的误导标注。

必须保持：
1) 记忆带 when 时，模块页条目输出「结构化条件」行（维度=取值，多值 /，多维中文逗号）。
2) 记忆带 enforced_by 且规则文件/符号仍在时，标题后标「（已由规则拦截）」；规则缺失、改过或找不到符号时改标「（规则需核实）」，勿当已拦住；条目仍列出「已由规则」链接；索引「最近更新 / 全项目通用」同样按此口径。
3) 无 when / 无 enforced_by 时不输出对应行或标注；applies / verify 原有展示不变。
4) 读码摘要与 --brief 共用 enforced_mark；延迟核对时用占位符，fill_stale 后按核对结果落成标注。
5) pmem wiki 与写入后自动生成共用 generate/wiki.py。

入口：src/pmem/core/entry.py（enforced_mark）；
src/pmem/generate/wiki.py；
src/pmem/hooks/memories.py；
src/pmem/cli/brief.py；
src/pmem/service/search.py（enforced_hint）。
