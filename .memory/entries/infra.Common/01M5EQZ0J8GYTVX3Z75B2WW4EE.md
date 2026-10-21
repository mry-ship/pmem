---
id: 01M5EQZ0J8GYTVX3Z75B2WW4EE
module: infra.Common
entity: Versioning
kind: decision
status: active
supersedes: []
anchors:
- pyproject.toml
- src/pmem/__init__.py
- tests/test_cli.py#test_version_flag_prints_version
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 父子模块与回复格式定为 v0.5；安装包版本号从 0.5.0 起与路线版本对齐
aliases:
- 版本号
- v0.5
- 发版
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
决定（2026-10-21，用户确认）：父子模块（模块名最多 4 段、继承、下级标题）、【pmem检索/查询/修改】回复格式、正文上限 5000 字这批改动定为 v0.5，而不是 v0.4。
原因：v0.4 已是“治理闭环”（Issue #14，已关闭），再用会和它混淆；模块名格式变化要求团队一起升级，属于次版本。
同时：pyproject.toml 与 src/pmem/__init__.py 原先一直是 0.1.0.dev0，和路线版本脱节，doctor 提示“团队需升级”时无法用 pmem --version 判断；
从 0.5.0 起安装包版本号与路线版本对齐（改版本要同时改这两处和手册页眉页脚，并 uv lock）。
test_cli 的版本测试改为读 __version__，不再写死。
设计文档第 14 节已加 v0.5 一行；GitHub Issue 尚未开。
