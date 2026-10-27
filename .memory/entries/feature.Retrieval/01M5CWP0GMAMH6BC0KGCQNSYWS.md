---
id: 01M5CWP0GMAMH6BC0KGCQNSYWS
module: feature.Retrieval
entity: Embedding
kind: correction
status: active
supersedes:
- 01M5CW5PV234V9YC6X1REW6NZX
anchors:
- src/pmem/index/embedder.py#embed_url
- src/pmem/index/embedder.py#_api_key
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 远程嵌入要本机明确打开，通用 OpenAI 密钥只发给官方地址
verify: uv run pytest tests/index/test_embedder.py
verified: '2026-10-27'
verified_at: '2026-10-27T17:32:43.454+08:00'
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
更正：仓库配置里的嵌入地址不再默认带走环境里的 OpenAI 密钥。
只允许本机和 https://api.openai.com；
其他地址要本机设 PMEM_EMBED_ALLOW_REMOTE=1，且必须是 https。
OPENAI_API_KEY 只发给官方地址，其余只用 PMEM_OPENAI_API_KEY。
请求不跟随跳转。
地址不合法时不建嵌入器，检索退回关键词。
