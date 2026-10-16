---
id: 01M52A5XFKT2P2DQQQGDKSZ84C
module: infra.Model
entity: ContentFormat
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/textfmt.py#format_content
- src/pmem/core/textfmt.py#_wrap_line
revision: git:b383fc9
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 断行
- 换行
- 一整行
- 缩进
- 可读性
- 格式化正文
---
决定：记忆正文写入文件前统一经 core/textfmt.py 的 format_content 断行，方便人直接打开 .md 阅读。

规则：
  1) 只处理超过 120 字的行；代码块（``` / ~~~）和表格行不动；
  2) 在句末标点（。！？；）后断开，后面紧跟右引号、右括号或另一个标点时不断；
  3) 行内编号（“：1) …；2) …”、“1、”、“(1)”、“①”）另起一行并缩进两格；
  4) Markdown 列表项断开后，续行按列表标记宽度缩进；
  5) 断出的碎片少于 6 个字时并回上一行；
  6) 括号没闭合时不断行，早期版本在括注里断开的行会在再次整理时并回。
只增加换行和缩进，不改文字；重复调用结果不变（测试守着）。

原因：从旧系统导入的记忆正文是一整行（TileMatch 1087 条里 993 条超过 150 字且无换行，最长 800 多字），打开文件很难读。

影响范围：record（MCP 和命令行）与 import 写入时自动整理；
已有文件用 pmem format [--apply] 一次性整理（TileMatch 1115 条、本仓库 80 条已整理）。
检索、BM25 分词不受影响（换行只是空白；句号本来就打断中文二元组）。
风险：正文以“1.”这类编号开头的数字被误当成编号的可能——已排除“2.5”这种小数；如出现误断，只影响换行，不影响内容。
