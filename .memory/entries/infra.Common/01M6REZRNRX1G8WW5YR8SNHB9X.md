---
id: 01M6REZRNRX1G8WW5YR8SNHB9X
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M6R9F4JYK1R5Z8MGH9YNS2AT
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 当前安装包 0.6.5：解释器识别与 MCP 路径修复，不占 v0.7
verify: uv run pmem --version；gh release view v0.6.5
applies: 发版或改路线表当前版本时
aliases:
- 0.6.5
- 发版
---
需求来源：0.6.4 已发布后，又修了终端解释器识别、MCP 启用和换行注入，需要单独发 0.6.5，不占 v0.7。

必须保持：安装包当前为 0.6.5（pyproject.toml、src/pmem/__init__.py、uv.lock 同步为 0.6.5）。0.6 补丁线，v0.7 类型安全仍进行中，不要跳 0.7.0。

v0.6.5：带版本号的 python（python3.12、python3.11.exe）事前读脚本；
doctor 认完整路径、单引号和 cmd /c；
Claude 按解析后的真实路径启用，不断网 UNC 上 resolve；
Codex 路径含单引号时用 TOML 基本字符串；
Cursor 同名目录保留其他配置哈希；
锚点、读回字段和闸门摘要里的换行收成一行。

README 徽章、路线表与 docs/pmem-guide.html 已同步到 0.6.5。

入口：README 路线表当前版本；GitHub Release v0.6.5；发下一个 0.6 补丁或改路线表当前版本时更新本条。
