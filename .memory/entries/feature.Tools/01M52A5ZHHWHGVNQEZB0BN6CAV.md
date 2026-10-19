---
id: 01M52A5ZHHWHGVNQEZB0BN6CAV
module: feature.Tools
entity: WriteFormat
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#record
revision: git:b383fc9
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 断行
- 一整行
verified: '2026-10-19'
---
决定：record 写入时把正文经 format_content 断行后再存（字数校验在断行之前做，换行不计入上限）。
原因：Agent 常把长结论写成一整行，打开文件难读；
断行只加换行和缩进，不改文字，返回的 content、检索结果随之是断行后的版本。
