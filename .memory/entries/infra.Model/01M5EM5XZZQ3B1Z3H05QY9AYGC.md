---
id: 01M5EM5XZZQ3B1Z3H05QY9AYGC
module: infra.Model
entity: Config
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
- src/pmem/service/record.py#_invalid_content
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 正文硬上限 write.content_max 默认 5000 字，建议值 600 字只提示不拒绝
verify: uv run pytest tests/test_service.py -k content_length
applies: 通过 MCP 或 pmem record 写入；项目 config.yaml 未覆盖 write.content_max 时
aliases:
- 字数上限
- 正文长度
- 字数超限
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
用户要求（2026-10-21）：正文硬上限从 1200 字放宽到 5000 字。
理由是做完大功能后的功能记录、合并多条零碎记忆后的现状常超过 1200 字；
本机近 30 天 4 次 content_length 拒绝分别是 1283、1335、1290、1264 字，都来自合并场景。
必须保持：write.content_max 默认 5000；write.recommend_max 仍为 600，超过只给写作提示、不拒绝；content_min 仍为 20。summary、applies、verify 的单独上限不变。
适用：未在 config.yaml 显式写 content_max 的项目走默认值；已接入项目的 config.yaml 写死了 1200，需要手动改（本仓库已改为 5000）。
入口：core/config.py 的默认配置；校验在 service/record.py 的 _invalid_content。
