---
id: 01M5M945KR6CQD0GJHTCV5PD1T
module: feature.Spec
entity: Reconstruct
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#_bodies
- src/pmem/cli/spec_cmd.py#run_spec
- src/pmem/generate/templates.py
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 补全规格入口是 pmem spec complete，须还原已实现对外契约至少九成八
verify: uv run pytest tests/test_spec.py
applies: 按 pmem-spec 写或补全模块规格时
aliases:
- 九成
- pmem spec complete
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
需求来源：用户要求补全模块规格达到九成八，并继续用反推补通用规则。
必须保持：用户说「补全模块规格」或运行 `pmem spec complete` 时走首稿加反推循环。
停手前规格必须能直接读到入参和出参字段闭集、失败条件、配置与环境变量、生成物、词表、决定表、须按字面抄的原文（带尖括号占位的模板全文，禁止「含某某」）、一轮例子、依赖规格。
九成八的分母是已实现的对外契约：入参、出参、词表、数字、对外文案、生成物结构、失败条件、配置键和环境变量。
源码行数、内部函数名、测试夹具、代码里没有的策划不计入分母。
complete 与 fill 只铺骨架、不写正文。
--check 仍只看空标记。
没有已登记模块时不建规格目录，也不说首稿都已写完。
入口：`pmem spec complete`；pmem-spec 技能。
