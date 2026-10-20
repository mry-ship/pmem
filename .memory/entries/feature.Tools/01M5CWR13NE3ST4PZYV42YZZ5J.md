---
id: 01M5CWR13NE3ST4PZYV42YZZ5J
module: feature.Tools
entity: Graph
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/service/base.py#_refresh_wiki
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: wiki.dir 指到项目外时跳过自动生成并只警告，记忆仍写入成功
verify: uv run pytest tests/test_wiki.py -k outside_project
applies: wiki.auto 为开（默认开）时，record 或 confirm 成功之后的自动生成
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
需求来源：用户 2026-10-20 要求先修 Wiki 路径。仓库配置里的 wiki.dir 可以指到项目外，写入记忆后会自动生成。
必须保持：wiki.dir 解析后不在项目内（绝对路径、..、指到项目外的符号链接）时，跳过自动生成，在返回的 warnings 里写明「wiki.dir 指向了项目目录以外，已跳过自动生成」。
记忆本身仍写入成功，不因此失败。
目录在项目内时仍照旧自动生成。
入口：service/base.py 的 _refresh_wiki，目录判断用 generate/wiki.py 的 project_wiki_dir。
