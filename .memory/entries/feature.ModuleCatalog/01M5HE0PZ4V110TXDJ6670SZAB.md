---
id: 01M5HE0PZ4V110TXDJ6670SZAB
module: feature.ModuleCatalog
entity: NameMatch
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py
revision: git:8d3a154
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: 路径匹配慢的根因：wcmatch globmatch 每次重新编译模式，改缓存 compile 后规划快一倍多
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
结论：registry._matches 原先对每个文件×每个带通配符的模式调 wglob.globmatch，它每次都重新编译（bracex 展开花括号）。
TileMatch 4681 个文件的 map_files 编译了 9 万次，占规划耗时约 80%（cProfile）。
现在用 lru_cache 缓存 wglob.compile 的结果（_compiled），规划 4.8 秒降到 2.1 秒；doctor、sync、seed、report、Hook 按路径找模块都受益。
以后新增通配符匹配不要再直接调 globmatch，走 _compiled(pattern).match(path)。
