---
id: 01M5KZTK4B475FFPA5F542NJQV
module: infra.Common
entity: Roadmap
kind: correction
status: active
supersedes:
- 01M5KTHT2192NX8XS0MAK8W89B
anchors: []
revision: git:ac31a91
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: v0.6 已发布，安装包版本是 0.6.0
verify: pmem --version 输出 pmem 0.6.0
applies: 排版本、改 README 路线表或总设计第 14 节时。
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
更正：模块规格发布时安装包已从 0.5.1 对齐到 0.6.0。
仍有效：模块规格是 v0.6（Issue #16），类型安全是 v0.7（Issue #15），范围不改。
对齐的位置：pyproject.toml、src/pmem/__init__.py、uv.lock、首页徽章、手册页眉页脚。
