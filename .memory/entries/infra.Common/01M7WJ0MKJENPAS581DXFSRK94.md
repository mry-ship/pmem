---
id: 01M7WJ0MKJENPAS581DXFSRK94
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: 当前安装包 0.7.0：类型安全与规则化已发布
verify: uv run pmem --version；gh release view v0.7.0
applies: 发版或改路线表当前版本时
verified: '2026-11-20'
verified_at: '2026-11-20T21:27:51.903+08:00'
---
需求来源：v0.7 设计范围内功能齐后发 0.7.0。

必须保持：安装包当前为 0.7.0（pyproject.toml、src/pmem/__init__.py、uv.lock 同步）。
本版含：enforced_by + health 规则候选、facets/when、边界校验、返回契约、pyright 基线。
README 徽章、路线表与 docs/pmem-guide.html（GitHub Pages）已同步到 0.7.0；效果栏「当前版本 0.7.0」用 2026-11-20 近 30 天 report。

入口：README 路线表当前版本；GitHub Release v0.7.0。
