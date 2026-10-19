---
id: 01M5A8G3D7FAKAB5SRK3X1A9HX
module: feature.ModuleCatalog
entity: NameMatch
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/registry.py#_matches
- src/pmem/catalog/sync.py#_existing_module
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 方括号目录
- 动态路由
- 冷候选
- 路径匹配不到
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定（2026-10-19 深度检查）：
1) 路径匹配：Next.js 的 app/[id]、app/{slug} 这类目录名本身带方括号、花括号，原先一律当通配符，app/[id]/** 永远匹配不到 app/[id]/page.tsx，sync 每次都会再提议一遍。
   现在按通配符匹配不上时，再把 []{} 转义按字面匹配一次（没有 * ? 时按前缀匹配）。
   仍保留旧行为：app/[id]/** 也会匹配 app/i/x。
2) sync 的 _existing_module：短名索引只含正式模块，与新目录同名的冷候选原先认不出：同大类时被误报成与废弃模块冲突，异大类时新建同名正式模块。现在短名解析不到时再按短名找唯一的冷候选，路径追加到它上面。
3) modules.yaml 和记忆文件的重写（yamlfile、migrate 搬文件）改用 core/fileio.write_atomic，见 feature.Storage。
