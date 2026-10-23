---
id: 01M5MCSDXTGTADZC2S545Y6EFD
module: feature.Spec
entity: Complete
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/spec_cmd.py#run_spec
- src/pmem/cli/main.py
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: pmem spec complete 铺骨架并要求正文写到九成八
verify: uv run pytest tests/test_spec.py -k complete
applies: 用户要一次补全模块规格时
aliases:
- pmem spec complete
- 补全入口
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
需求来源：用户要求加一条命令作为补全入口，随后把目标从九成提高到九成八。
必须保持：`pmem spec complete` 与 `fill` 同一实现：铺骨架、列出空标记还在的模块、不写正文。
有未完成时返回 1，都去掉返回 0。
标准输出先打「补全模块规格：本命令铺骨架并列出缺谁，正文由 Agent 按 pmem-spec 写到至少九成八。」
未完成提示含失败条件、配置与环境变量。
没有已登记模块时不建规格目录，也不说首稿都已写完。
`--check` 仍只看空标记。
适用：用户要一次补全模块规格时。
入口：终端 `pmem spec complete`；对 Agent 说「补全模块规格」时技能先跑这条。
