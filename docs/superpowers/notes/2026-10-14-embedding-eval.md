# 嵌入模型评测（M3）

- 评测集：`tests/fixtures/eval/retrieval.yaml`（20 条游戏项目记忆、20 个查询，含同义改写、中英混合、代码标识符）
- 方式：全局检索（不限模块），看期望记忆是否排在第 1 / 前 3；脚本 `scripts/eval_retrieval.py`
- 机器：Windows 11，Python 3.12，CPU 推理

| 方案 | 前 1 | 前 3 | 加载 | 20 次查询 |
|---|---|---|---|---|
| 纯关键词（中文二元组 + 英文词 BM25） | 18/20 | 20/20 | 0 s | 0.2 s |
| 关键词 + `BAAI/bge-small-zh-v1.5`（ONNX，90 MB） | 19/20 | 20/20 | 1.2 s | 0.3 s |
| 关键词 + `paraphrase-multilingual-MiniLM-L12-v2`（ONNX，220 MB） | 19/20 | 20/20 | 1.1 s | 0.6 s |
| 关键词 + Ollama `nomic-embed-text` | 18/20 | 20/20 | 0 s | 47 s |

## 结论

1. 记忆按模块过滤后候选很少，**纯关键词已能满足大多数检索**；语义模型只在改写类查询上多对 1 题。
2. 默认安装不带嵌入模型（零下载、零等待）；`embedding.backend: auto` 在装了 `pmem[embed]` 时自动使用 `BAAI/bge-small-zh-v1.5`，否则用关键词。
3. Ollama 后端保留给已有 Ollama 的团队，不作默认。
4. 评测集偏容易，后续用真实项目的记忆扩充后再复评。
