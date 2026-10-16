---
id: 01M51QHBMF3YCZN9AX44HZTGDK
module: feature.Retrieval
entity: StaleCheck
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/index/anchors.py#symbol_block
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 需核实
- 过期
- 误报
- stale
---
结论：“需核实”（stale）原先只按文件判断：关联文件在核对日期之后有任何提交就标过期。本仓库 16 条被标“需核实”，逐条核对后全部仍然成立，误报主要来自同一文件里改了别的函数（gate.py、store.py 几乎每天都改）。

现在的判定（检索、memory_graph、读代码摘要、拦截提示、Wiki 共用同一个检查器）：
- 文件已删除：标“已不存在”；
- 锚点写成 `路径#函数名` 且当前文件里找不到该函数：标“找不到”；`类.方法`、`类::方法` 取最后一段；
- 文件在基准日（核对日期；7 天内提交的记忆取提交日）之后改过：Git 下取基准日那版文件，提取该函数的代码块比较。
  Python 按缩进取块（支持多行签名），其他语言按花括号配对；
  调用语句（return/if 开头、分号结尾）不当成定义。
  代码块相同就不算过期，不同则提示“X 中 函数 在 日期 之后改过”；
- SVN、没有历史、旧版里找不到函数时退回按文件判断。

效果：本仓库误报从 16 条降到 12 条，剩下的基本是只写了文件的锚点；核对后已全部 confirm。写记忆时 anchors 应尽量写到函数。
