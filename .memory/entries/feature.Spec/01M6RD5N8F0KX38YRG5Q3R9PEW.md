---
id: 01M6RD5N8F0KX38YRG5Q3R9PEW
module: feature.Spec
entity: RebuildSpec
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#spec_prefill
- src/pmem/generate/spec.py#_prefill_lines
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 规格预填会把带换行的锚点原样写进程序设计
verify: 锚点含换行时程序设计.md 的入口列表被拆开
applies: pmem spec 从 feature 记忆预填入口
---
spec 预填把 feature 记忆的 anchors 原样写进程序设计.md 的「入口」列表（_prefill_lines 只加「  - 」前缀）。
写入 API 的 _normalize_anchor 只改斜杠和相对路径，不把内部换行压成一行；
从磁盘读回时 anchors 也是 str()，不经过 _text。

锚点若含换行（手改 YAML，或双引号里的 \n），会把规格正文拆开，后面的行不再是列表项。规格技能要求对照这些栏目写，甚至有「原文须按字面抄」。不要把预填内容当成已经消毒过的单行事实。

标题走 summary/_text 或 auto_summary，会收成一行。注入口在锚点，不在标题。
