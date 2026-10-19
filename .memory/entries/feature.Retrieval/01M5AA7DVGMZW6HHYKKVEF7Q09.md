---
id: 01M5AA7DVGMZW6HHYKKVEF7Q09
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes:
- 01M51QHBMF3YCZN9AX44HZTGDK
- 01M5A8FXTVESH9AFXBXJSC555N
anchors:
- src/pmem/index/anchors.py#symbol_block
- src/pmem/index/anchors.py#AnchorChecker
- src/pmem/index/store.py#refresh
revision: git:8e4415f
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 需核实
- 过期
- stale
- 锚点
- 记忆与代码不一致
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
更正（合并两条旧记忆的现行规则）：“需核实”（stale）的判定由 AnchorChecker 统一完成，检索、memory_graph、读代码摘要、拦截提示、Wiki 共用。
- 锚点文件已删除：标“已不存在”；
- 锚点写成 路径#函数名 且当前文件里找不到：标“找不到”；
- 文件在基准日（核对日期；7 天内提交的记忆取提交日）之后改过：Git 下取基准日那版文件，提取该函数的代码块比较，相同不算过期，不同提示“X 中 函数 在 日期 之后改过”；Python 按缩进取块，其他语言按花括号配对；
- SVN、没有历史、旧版里找不到函数时退回按文件判断。

更正点：“类.成员”“类::成员”原先取最后一段、按成员名取文件里第一个定义，导致 MemoryIndex.close 取到 VectorCache.close（漏报加误报）。
现在先找类的代码块再在类里找成员（跳过类头，构造函数 Shop.Shop 能找到），找不到类时退回按成员名找。
另：索引刷新时记忆文件变成无法解析会递增 version；stat 前文件被移走不再报内部错误。
写记忆时 anchors 尽量写到函数，只写文件的锚点误报最多。
