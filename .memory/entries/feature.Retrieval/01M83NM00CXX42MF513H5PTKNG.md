---
id: 01M83NM00CXX42MF513H5PTKNG
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes:
- 01M5CKQ4AGMSE093QEHFG1QM8B
- 01M5YT0PZFD2WQ2GVTK21K9TJV
anchors:
- src/pmem/index/anchors.py#_python_block
- src/pmem/index/anchors.py#_python_code
- src/pmem/vcs/git.py#GitVCS.changed_since
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 函数块用语法树；未跟踪新文件也标需核实
aliases:
- 需核实
- stale
- 未跟踪
source:
  kind: document
---
更正（均已按此实现）：
1) Python 函数块用 ast 的 lineno/end_lineno 和 decorator_list，含多行装饰器；
   「类.成员」先找类再找成员。
   解析失败或找不到符号时退回缩进/花括号；
   回退路径认反斜杠转义。
   同一文件新旧一版能解析、一版不能时可能误报需核实，只发生在有语法错误的版本上，宁可误报。
   语法树按文本缓存。
2) Git 未跟踪的新文件后来改了也要标需核实：changed_since 除 git diff HEAD 外，再 git ls-files --others --exclude-standard，按 mtime 与基准比。
   写记忆之前就改好、还没提交的不算之后改过。
   被忽略的文件不报。
   SVN 未纳入版本库的文件仍不报（工程目录 mtime 误报多，宁可漏报）。

合并自 2 条更正。
