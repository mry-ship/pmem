---
id: 01M59J8HNBSXB4P8BZ2GTTDN1Q
module: feature.Wiki
entity: Generate
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py#write_wiki
- src/pmem/cli/wiki_cmd.py#run_wiki
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 覆盖手写文档
- wiki 输出目录
- 生成标记
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：pmem wiki 只覆盖自己生成的页面（文件开头是生成标记 MARKER）。同名文件是手写的就跳过，写入 WikiResult.skipped，命令列出这些页面并返回 1。
原因：wiki 目录可配置，常被指到 docs/ 这类已有手写文档的目录；原先同名页面（如 index.md）会被直接覆盖，而清理阶段只删带标记的旧页，写入时却没有同样的保护。
处理办法：改名手写文件，或把 wiki 输出目录换到独立子目录。
