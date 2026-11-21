---
id: 01M7Z7VTY8C2EAXH19P9E0MFMK
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M7XBDEG05WPVXFM1QVJ7X3W0
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 当前安装包 0.7.3：工程质量、规格先读与阅读顺序
verify: uv run pmem --version；gh release view v0.7.3
applies: 发版或改路线表当前版本时
aliases:
- 版本号
- 发版
- 0.7.3
source:
  conversation: dfe5efd8-5694-4dd1-a697-c16f1ce9cd6a
---
需求来源：0.7.2 之后把工程质量技能、规格默认先读和阅读顺序收成 0.7.3 发布。

必须保持：安装包当前为 0.7.3（pyproject.toml、src/pmem/__init__.py、uv.lock 同步）。
本版相对 0.7.2：工程质量规则与 pmem-minimal、pmem-review 独立于记忆规则，不改 KINDS、检索排序和 bench 开关；
spec.reminder 与 spec.read_before_edit 缺省开启，已写完的程序设计和模块现状没读过就先拦住，空骨架不要求，记忆闸门优先于规格闸门；
reading_hint 只在过期、有前提或多条时给一次，不改变排序。
README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.7.3。效果栏「当前版本 0.7.3」沿用 2026-11-21 近 30 天 report，因为本版不改检索排序和采用判定。

入口：README 路线表当前版本；GitHub Release v0.7.3。
