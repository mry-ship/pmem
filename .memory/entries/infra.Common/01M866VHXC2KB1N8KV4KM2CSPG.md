---
id: 01M866VHXC2KB1N8KV4KM2CSPG
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M83T9KX8ZV27A6QF461S47GB
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:183b8bc
author: 1002378395@qq.com
note_date: '2026-11-24'
summary: 首页、手册、架构与路线表已同步到 0.7.6
verify: README 与手册含「当前版本 0.7.6」；architecture 文首含 0.7.6；路线表 v0.7.6 标当前版本
applies: Wiki 是独立仓库，只推 master 不会更新 Wiki。
aliases:
- 手册
- 0.7.6
source:
  kind: human
valid_from: '2026-11-24'
---
需求来源：发 0.7.6 时要求更新手册和 GitHub 主页。
必须保持：README 与 docs/pmem-guide.html 写「当前版本 0.7.6」；
徽章、能力行、路线表、页脚与「当前发布包」同为 0.7.6；
v0.7.5 能力行保留为历史。
architecture 文首与设计 §14 当前版本是 0.7.6，写明规格两项缺省关闭。
效果数字仍写 2026-11-21。
适用条件：Wiki 是独立仓库，只推 master 不会更新 Wiki。
入口：README.md、docs/pmem-guide.html。
