---
id: 01M7XBDEG05WPVXFM1QVJ7X3W0
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M7WV3M8GAQFVKRKQ3GXPF4VD
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 当前安装包 0.7.2：来源、生效日与 spec closed
verify: uv run pmem --version；gh release view v0.7.2
applies: 发版或改路线表当前版本时
aliases:
- 版本号
- 发版
- 0.7.2
source:
  kind: conversation
---
需求来源：0.7.1 之后把来源、生效日和规格闭集核对收成 0.7.2 发布。

必须保持：安装包当前为 0.7.2（pyproject.toml、src/pmem/__init__.py、uv.lock 同步）。
本版相对 0.7.1：source.kind 只标证据来源，不写入 verified，不参与排序；
valid_from 只影响 as_of，现行检索不隐藏未来生效的记忆，替代要到生效日才算；
pmem spec closed 只读核对闭集，只出一致、可能不一致、无法判断。
README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.7.2。效果栏「当前版本 0.7.2」沿用 2026-11-21 近 30 天 report，因为本版不改检索排序和采用判定。

入口：README 路线表当前版本；GitHub Release v0.7.2。
