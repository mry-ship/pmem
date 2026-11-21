---
id: 01M7YYGXTKRYH03BPSTDEV9H8B
module: feature.Spec
entity: ReadForChange
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#spec_prefill
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 编码前读规格按字面用闭集，预填待核对不算数
verify: 规格仍有「待对照代码核对」或 spec:empty 时，不把该节当已核对契约
applies: 编码前根据已有模块规格决定改法时
aliases:
- 读规格
- 必须保持
- 待核对
source:
  conversation: dd30165a-9192-4f39-b74b-d91fa990fa34
---
决定：编码任务里读已有规格时，程序节的入参出参闭集、失败条件和原文模板按字面使用，不收成「必须保持」的大意。
现状节的必须保持也要读。
带「待对照代码核对」的预填行，以及仍有空标记的节，只是起点，先对照代码。
--check 通过也不等于这份规格已能单独当契约。
没选：在同一次编码里跑 pmem spec complete。那是补写规格的入口，会要求正文写到九成八。
排除项和根因不进规格，仍要查记忆。
