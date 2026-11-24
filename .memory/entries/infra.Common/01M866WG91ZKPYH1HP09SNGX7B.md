---
id: 01M866WG91ZKPYH1HP09SNGX7B
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M83T9BWRPYJPWT2WG8GMYX5Z
anchors:
- src/pmem/__init__.py
- pyproject.toml
revision: git:183b8bc
author: 1002378395@qq.com
note_date: '2026-11-24'
summary: 当前安装包是 0.7.6，规格两项缺省关闭
verify: pmem --version 输出 pmem 0.7.6；pyproject、__init__.py、uv.lock 同为 0.7.6；test_evidence_version_is_076
applies: 发布包是 GitHub Release v0.7.6，不上 PyPI。
aliases:
- 0.7.6
- 发版
source:
  kind: human
valid_from: '2026-11-24'
---
需求来源：发 0.7.6 时把安装包、首页和手册对齐。
必须保持：pmem --version 输出 pmem 0.7.6；
pyproject、src/pmem/__init__.py、uv.lock 是同一个版本。
适用条件：当前发布包是 GitHub Release v0.7.6，不上 PyPI。
入口：pmem --version。
相对 0.7.5：spec.reminder 与 spec.read_before_edit 缺省改回关闭。
没写这两项的旧配置升级后不再提醒，也不再拦未读规格；文件里已经写成 true 的保持开启。
不改检索排序和采用判定，效果数字仍是 2026-11-21 近 30 天报告。
