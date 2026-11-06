---
id: 01M6QXBRWT54MJP4SD69GP4P8E
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M641EMQVGN2NXPGY2TR3EFZY
anchors:
- pyproject.toml
- src/pmem/__init__.py
revision: git:a0c3d8f
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 当前安装包 0.6.2：Hooks=full 与防弹窗补丁，不占 v0.7
verify: uv run pmem --version；gh release view v0.6.2
applies: 发 0.6 补丁或改 README 路线当前版本时
---
需求来源：用户要求在 GitHub 打最新包。
必须保持：安装包、README 徽章与路线表、手册页眉页脚、uv.lock、src/pmem/__init__.py 同为 0.6.2。这是 0.6 补丁，不占 v0.7。
v0.6.2 内容：默认 Hooks=full；CREATE_NO_WINDOW 藏窗；Windows+Cursor 清空 Claude Hooks；init 启用 MCP；模块路径挂靠与双周 health 文档。
入口：GitHub Release v0.6.2；安装见 Release 说明。
