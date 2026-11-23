---
id: 01M83NXHX64QDZPKYMPZBXH3KF
module: feature.Gate
entity: SpecRead
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/guard.py#_spec_excerpt
- .memory/specs/feature.Gate/程序设计.md
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 规格拦截摘录只取文件开头 800 字，闭集和失败条件通常不在里面
verify: 程序设计.md 前 800 字不含「入参字段闭集」；state.py 的 _DEFAULTS 含 spec_read
applies: spec.read_before_edit 为真、闸门为 block，拒绝文案附规格摘录时
aliases:
- 摘录截断
- 规格摘录
- 800字
source:
  conversation: b0769dda-9730-42f8-84a2-6bf9080d94b7
  kind: code
---
风险：规格拦截附的摘录只有文件开头 800 字，而 block 在本对话还没记到任何一次成功读取时，摘录给过再改就放行。放行依据里通常没有要守住的契约。
原因：_spec_excerpt 从正文起始截到 _SPEC_EXCERPT（800）。
模块规格的前面是所有权和入口，入参/出参闭集、须按字面抄的原文、失败条件写在后面。
feature.Gate 的程序设计.md 约 8804 字，前 800 字停在「stop 用 followup_」。
同一份规格还有一处漏：会话字段闭集仍停在 spec_nudged，没有 spec_read、spec_warned、spec_offered；
文件头 updated 仍是 2026-10-29。
spec closed 只核对「一行一个字段名」的入参节，看不到这段散文清单。
