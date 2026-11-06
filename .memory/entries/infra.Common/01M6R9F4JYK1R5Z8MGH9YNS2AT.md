---
id: 01M6R9F4JYK1R5Z8MGH9YNS2AT
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M6R2288G9XEN3G52QKN89JG6
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 当前安装包 0.6.4：shell.py 拆包 + spec 从 feature 记忆预填，不占 v0.7
---
需求来源：发 v0.6.4 后更新当前版本口径。

必须保持：安装包当前为 0.6.4（pyproject.toml 与 src/pmem/__init__.py 同步为 0.6.4）；0.6 补丁线，v0.7 类型安全仍进行中，不要跳 0.7.0。

v0.6.3：锚点越界读校验 + Cursor 运行时 MCP 批准被覆盖的修复。
v0.6.4：hooks/shell.py 拆成 shell/ 包（constants/lexer/targets/__init__，对外 7 名不变）；
pmem spec 从现行 feature 记忆预填程序节入口、现状节必须保持（标待核对，EMPTY 与九成八口径不变）。

README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.6.4。

入口：README 路线表当前版本；GitHub Release v0.6.4；发下一个 0.6 补丁或改路线表当前版本时更新本条。
