---
id: 01M83R4D4KHKZE3V588Y9X5DEH
module: feature.Spec
entity: ClosedSetCheck
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/spec_closed.py#_sections
- src/pmem/generate/spec_closed.py#_param_annotations
- src/pmem/generate/spec.py#_bodies
- src/pmem/hooks/guard.py#_contract_text
revision: git:223a61d
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 未知标题不结束当前节；字段签名不绑入口
verify: 对 .memory/specs/feature.Gate/程序设计.md 跑 _sections：出参正文含「生成物：」，且没有「入口」键。_contract_text
  的失败条件摘录也含「生成物：」
applies: 跑 pmem spec closed，或改 _sections / _param_annotations / _contract_text 时
aliases:
- 章节串读
- 字段签名误报一致
source:
  conversation: e0ffd8af-3de7-48fb-8ac0-0d832c508a60
  kind: code
---
现象：spec closed 的 _sections 只有整行去掉末尾冒号后恰好是「入口 / 入参字段闭集 / 出参字段闭集 / 原文（须按字面抄） / 必须保持」才切换章节。
未知标题（失败条件、配置与环境变量、生成物，以及 ### 标题）不会把 current 置空，后文继续归入上一节。
同一行写成「入口：后面还有字」或「## 入口：」也不开节。

guard._contract_text 是同一类扫描：只在六个契约标题处切换，未知标题不结束当前节。它认得「标题：」和同一行的第一句，但 ## 标题同样不切换。

证据：骨架顺序是出参字段闭集之后接数据形状、所有权、决定表、失败条件、配置、关键流程、生成物，再到原文。
当前 feature.Gate 程序设计里，出参字段闭集扫出 39 行，正文含失败条件、配置与环境变量、生成物；
入口键缺失，因为该行是「入口：`pmem hook …`」。
构造「入口：」后接「失败条件：」时，失败条件的锚点仍留在入口里。
同一份文件的契约摘录里，会话字段闭集含决定表和关键流程，失败条件含配置与环境变量和生成物。

_param_annotations 遍历模块内全部函数，不对照入口符号。无关函数的同名带注解参数会让该字段报一致。后文若不是一行一个字段，整节会变成「无法判断」。

影响：核对器会多报锚点、丢掉入口，或给出错误的一致；闸门摘录会把别的章节混进契约。tests/test_spec_closed.py 没有这两种用例。
没选：把这当成新的规格类型或改三态输出。
