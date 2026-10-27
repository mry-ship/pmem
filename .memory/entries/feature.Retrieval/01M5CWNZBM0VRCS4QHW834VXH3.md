---
id: 01M5CWNZBM0VRCS4QHW834VXH3
module: feature.Retrieval
entity: Embedding
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/embedder.py#embed_url
- src/pmem/index/embedder.py#_api_key
- src/pmem/index/embedder.py#make_embedder
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 嵌入地址只允许本机和官方 OpenAI；通用密钥不发给其他地址
verify: uv run pytest tests/index/test_embedder.py
aliases:
- base_url
- 密钥外带
- PMEM_EMBED_ALLOW_REMOTE
verified: '2026-10-27'
verified_at: '2026-10-27T17:32:43.454+08:00'
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
需求来源：2026-10-20 安全审查，仓库配置里的嵌入地址会带走环境里的 OpenAI 密钥和记忆正文。
必须保持：
- embedding.base_url 只接受本机（localhost、127.0.0.1、::1）、https://api.openai.com，或其他 https 地址且本机设了 PMEM_EMBED_ALLOW_REMOTE=1。
  仓库配置不能自己打开远程。
  file://、带账号密码的地址、元数据地址都拒绝。
- OPENAI_API_KEY 只发给官方地址。本机和其他远程地址只用 PMEM_OPENAI_API_KEY。
- 嵌入请求不跟随跳转。
- 地址不允许时 make_embedder 返回空嵌入器和原因，检索退回关键词，不发请求。
入口：index/embedder.py 的 embed_url、make_embedder。Ollama 默认仍是 http://localhost:11434。
