---
id: 01M5A8NBZE5S147NH20GDTWJ8J
module: infra.Model
entity: TextFormat
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/core/textfmt.py#_join_bracket_splits
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 括号吞行
- 换行丢失
- 格式化
- format
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
结论：记忆正文整理（textfmt）合并“被换行拆开的括号”时，原先只要括号没闭合就一直往下吞行；正文里有一个不成对的左括号（例如“（见下”漏写右括号）时，后面整段多行内容会被并成一行，列表结构全丢。
处理：只在 3 行以内（_MAX_BRACKET_LINES）能找到闭合括号时才合并，否则保持原样。
影响范围：pmem format 和写入时的自动整理。风险：括号内容真的跨 4 行以上时不再合并，需要作者自己整理。
