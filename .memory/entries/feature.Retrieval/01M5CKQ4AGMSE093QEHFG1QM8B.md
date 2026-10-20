---
id: 01M5CKQ4AGMSE093QEHFG1QM8B
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_python_block
- src/pmem/index/anchors.py#_python_code
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Python 函数块改用语法树截取，顶格字符串、多行装饰器、转义引号已不再截错
verify: uv run pytest tests/index/test_anchors.py -k "flush_left or multiline_decorator
  or escaped_quote"
aliases:
- 函数锚点
- 符号块
- 漏报
- 误报
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
更正（已修复）：symbol_block 原先按缩进截取 Python 函数块，2026-10-20 实测三类输入会截错：函数体里顶格的三引号字符串让块提前结束（漏报）；
签名默认值里的转义引号让括号配不平、块延伸到文件末尾（误报）；
多行参数的装饰器合并不进来（漏报）。
现在：先用 ast 解析整个文件，按 lineno / end_lineno 和 decorator_list 取起止行；“类.成员”在语法树里先找类再找成员，找不到类时按成员找，与文本规则一致。
解析失败（改到一半的语法错误、非 Python 文件）或语法树里找不到符号时，退回原来的缩进与花括号规则；回退路径的 _python_code 已认反斜杠转义。
约束：解析结果按文本缓存 32 份（lru_cache），长驻 MCP 进程同一文件不重复解析。
同一文件新旧两版一个能解析、一个不能时，两版走不同规则，块形状可能不同而误报“需核实”；这只发生在有语法错误的版本上，宁可误报。
本仓库真实数据：修复前后“需核实”的记忆集合除这条草稿外没有变化。
