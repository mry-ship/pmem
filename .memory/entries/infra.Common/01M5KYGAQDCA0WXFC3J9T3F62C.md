---
id: 01M5KYGAQDCA0WXFC3J9T3F62C
module: infra.Common
entity: SpecFill
kind: feature
status: active
supersedes: []
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: pmem spec 增加 fill：铺骨架并列出还没写完的模块
verify: uv run pytest tests/test_spec.py -q -k fill
applies: 使用 pmem spec 的子命令时
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
需求来源：用户要一个可以手动调用的入口，用来把模块规格补全。
必须保持：pmem spec 的 action 含 fill。铺骨架、列表和退出码在 feature.Spec。命令本身不写四份正文。
入口：pmem spec fill。
