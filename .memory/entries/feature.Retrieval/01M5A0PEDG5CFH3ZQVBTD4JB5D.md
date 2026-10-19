---
id: 01M5A0PEDG5CFH3ZQVBTD4JB5D
module: feature.Retrieval
entity: Embedding
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/store.py#VectorCache._conn
- src/pmem/index/store.py#VectorCache.get_many
- src/pmem/index/store.py#VectorCache.put_many
revision: git:4e8ab24
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- vectors.db
- 向量库
- 向量缓存
- sqlite
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：向量缓存 VectorCache 改为第一次真正读写向量时才打开 vectors.db（sqlite，WAL）。
原因：原先构造 MemoryIndex 就连接数据库、建表，只用关键词检索的进程（Hook、命令行 search/record、embedding.backend=none 的项目）也会建 vectors.db 并做一次写操作（issue #11）。
影响：内存里已有向量时不碰数据库；关键词检索、找相近记忆（只用 BM25）都不再打开它；reindex 删除缓存文件的逻辑不变。
验证：单测确认 embedder=None 检索后 vectors.db 不存在，启用向量检索后生成；全量测试通过。
