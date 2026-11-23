---
id: 01M83T9BWRPYJPWT2WG8GMYX5Z
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M83QE4PN1VCCSK00ZG4TB5A0
anchors:
- pyproject.toml
- src/pmem/__init__.py
- uv.lock
revision: git:223a61d
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 当前安装包是 0.7.5，不改检索排序和采用判定。
verify: pmem --version 输出 pmem 0.7.5；pyproject、__init__.py、uv.lock 同为 0.7.5；test_evidence_version_is_075。
applies: 发布包是 GitHub Release v0.7.5，不上 PyPI。
aliases:
- 版本号
- 发版
- release
source:
  conversation: e0ffd8af-3de7-48fb-8ac0-0d832c508a60
  kind: conversation
valid_from: '2026-11-23'
---
需求来源：发 0.7.5 时把安装包、首页和手册对齐。
必须保持：pmem --version 输出 pmem 0.7.5；
pyproject、src/pmem/__init__.py、uv.lock 是同一个版本。
适用条件：当前发布包是 GitHub Release v0.7.5，不上 PyPI。
入口：pmem --version。
相对 0.7.4：规格核对遇到 Markdown 标题和骨架其他栏目就结束当前节；
带类型的字段只对照入口路径#符号；
同一条 Read 有一条失败就不算已读。
不改检索排序和采用判定，效果数字仍是 2026-11-21 近 30 天报告。
