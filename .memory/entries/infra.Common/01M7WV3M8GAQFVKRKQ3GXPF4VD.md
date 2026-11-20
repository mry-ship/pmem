---
id: 01M7WV3M8GAQFVKRKQ3GXPF4VD
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M7WJ0MKJENPAS581DXFSRK94
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:a136be1
author: 1002378395@qq.com
note_date: '2026-11-21'
summary: 当前安装包 0.7.1：规则双态标注与 Watchdog 重试补丁
verify: uv run pmem --version；gh release view v0.7.1
applies: 发版或改路线表当前版本时
---
需求来源：0.7.0 之后补规则标注双态、doctor when 可见性、Watchdog WinError 6 重试，发 0.7.1 补丁。

必须保持：安装包当前为 0.7.1（pyproject.toml、src/pmem/__init__.py、uv.lock 同步）。
本版相对 0.7.0：enforced_mark 双态（已由规则拦截 / 规则需核实）、doctor when↔facets 对照与单测、Wiki/brief/MCP/health 文案对齐、Watchdog 子进程 WinError 6 短重试。
README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.7.1；效果栏「当前版本 0.7.1」用 2026-11-21 近 30 天 report。

入口：README 路线表当前版本；GitHub Release v0.7.1。
