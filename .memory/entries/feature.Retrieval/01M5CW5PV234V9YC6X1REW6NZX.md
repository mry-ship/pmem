---
id: 01M5CW5PV234V9YC6X1REW6NZX
module: feature.Retrieval
entity: Embedding
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/index/embedder.py#OpenAIEmbedder
- src/pmem/index/store.py#_vectors_for
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 仓库配置里的嵌入地址会带走环境里的 OpenAI 密钥和记忆正文
verify: 把 base_url 指到非本机后做一次语义检索，确认请求头里没有环境变量中的密钥，或该后端被拒绝
aliases:
- SSRF
- 密钥外带
- base_url
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
风险：embedding.backend 和 base_url 来自仓库的 .memory/config.yaml，没有允许名单，也不限于本机。
backend 为 openai 时，index/embedder.py 的 OpenAIEmbedder 把 PMEM_OPENAI_API_KEY 或 OPENAI_API_KEY 放进 Authorization，POST 到该地址。
缺向量时 store.py 的 _vectors_for 会把条目的议题、标题、正文、验证方法和别名一起发出去，查询词同样送出。
backend 为 ollama 时不带密钥，正文仍会发出去。
默认 auto 走本机 ONNX，不会自己发出去。要配置被改成远程后端，第一次语义检索才成立。
