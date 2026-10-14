---
id: 01M4X40BBTRXTJT8KJS5DJ3AB0
module: feature.Retrieval
entity: Embedding
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/embedder.py#make_embedder
revision: git:e258c6e
author: 1002378395@qq.com
note_date: '2026-10-14'
---
决定：默认只用关键词检索（中文相邻二字 + 英文整词/驼峰拆分的 BM25）；装了 pmem[embed] 时 backend=auto 自动叠加 BAAI/bge-small-zh-v1.5（ONNX，90 MB）。

排除：不用 SQLite FTS5 trigram，因为 trigram 至少 3 个字符，匹配不到“奖励”这类两字中文词。

依据：20 条记忆 / 20 个查询的评测（scripts/eval_retrieval.py），纯关键词前 1 命中 18/20、前 3 命中 20/20；bge-small-zh 前 1 为 19/20，加载 1.2 秒；多语言 MiniLM 同为 19/20 但体积 220 MB；Ollama nomic-embed-text 为 18/20，且 20 次查询耗时 47 秒。

风险：评测集偏容易，积累真实记忆后应复评。
