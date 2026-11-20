---
id: 01M7X5Z518KBRHTHEBXDK1DCDX
module: feature.Spec
entity: ClosedSetCheck
kind: plan
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#spec_prefill
revision: git:410ca2a
author: yanghu
note_date: '2026-11-21'
summary: 规格核对只读闭集，命令只自动输出三档
verify: 新核对不写 .memory/specs；pmem spec --check 仍只看空标记；无人工记录时不出现已确认不一致
applies: 做规格与代码一致性核对时
aliases:
- 规格一致性
- 闭集核对
---
规划：下一阶段的规格核对是只读闭集，不另做会改写规格的审查。

命令自动只输出三档：一致、可能不一致、无法判断。已确认不一致必须已有负责人的记录；命令不创建这一档，也不为它改规格。解析不出字段清单、签名或符号时输出无法判断，不用模糊匹配凑一致。原文里的尖括号占位按通配，不把整句判成不一致。

比对范围：程序节已写下的入参和出参字段名、原文栏整句、入口锚点路径或符号是否还在。职责、流程、技术方案，以及策划是否偏离，都标无法判断，不另设一档。

必须保持只核对原句还在、锚点还在。行为是否仍成立标无法判断。design-gap 不报不一致。

命令不写规格文件。pmem spec --check 仍只看空标记，新核对不并进 --check。
