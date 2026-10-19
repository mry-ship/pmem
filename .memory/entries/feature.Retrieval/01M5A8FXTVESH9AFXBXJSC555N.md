---
id: 01M5A8FXTVESH9AFXBXJSC555N
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#symbol_block
- src/pmem/index/anchors.py#_block
- src/pmem/index/store.py#refresh
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 需核实
- 过期误报
- 同名方法
- stale
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
更正：“类名.成员”形式的锚点原先核对时丢掉类名，只按成员名取文件里第一个定义。
现象：symbol_block(store.py, "MemoryIndex.close") 返回的是 VectorCache.close；
只改 MemoryIndex.close 时记忆不标“需核实”（漏报），改 VectorCache.close 反而标（误报）。
__init__、close 这类常见名最容易撞。
现在先找到类的代码块，再在类里找成员（跳过类头那一行，构造函数 Shop.Shop 能找到）；找不到类时退回按成员名找。
另：索引刷新时记忆文件变成无法解析（合并冲突标记、YAML 写坏）原先不递增 version，memory_graph 的缓存会继续用旧内容；
列出文件后 stat 前文件被移走（migrate、切分支）会抛 FileNotFoundError 让整次调用报内部错误。
两处都已修。
