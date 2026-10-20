---
id: 01M5CR8S8YZFXPVWY0EQD4ZQT6
module: infra.Model
entity: TextFormat
kind: correction
status: active
supersedes:
- 01M5A8NBZE5S147NH20GDTWJ8J
anchors:
- src/pmem/core/textfmt.py#_join_bracket_splits
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 正文整理只并回句末标点后断开的括号，作者在括号里自己换的行保留
verify: uv run pytest tests/core/test_textfmt.py
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
更正：旧结论只限制了“3 行内能闭合才合并”，但只要括号没闭合就并行，作者自己写的 foo(a,换行 b) 这类换行也会被并掉，违反“只增加换行和缩进、不改文字”。
现在只在上一行以 。！？； 结尾时才并回——这正是早期版本在括注里断行的形态；其他括号内换行保持原样。
仍有效：只在 3 行（_MAX_BRACKET_LINES）内能找到闭合括号时才合并，不成对的左括号不会吞掉后面的多行。
影响范围：pmem format 和写入时的自动整理。风险：括号内容真的跨 4 行以上时不再合并，需要作者自己整理。
