---
id: 01M5KYGAFK4CYA7JFP35ZVP486
module: feature.ModuleCatalog
entity: SpecSkeleton
kind: feature
status: active
supersedes: []
anchors: []
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 同步写入新模块后只补规格骨架，不写四份正文
verify: uv run pytest tests/test_spec.py -q
applies: pmem sync --apply 或 pmem sync --auto 真正写入了模块名单时
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
需求来源：用户（2026-10-23）要求后续自动补模块时也补规格。
必须保持：pmem sync --apply 写入后，以及 pmem sync --auto 实际追加了模块时，给还没有规格的已登记模块补四份骨架。
已有文件不覆盖。
不写四份正文。
这一轮新写出骨架时，提示对 Agent 说「补全模块规格」。
只预览时不写规格。
自动登记仍然只追加模块名单，不改已有模块名。
入口：pmem sync --apply、pmem sync --auto。
