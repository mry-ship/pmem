---
id: 01M5CVNFN8A60CYX8EVE220CWA
module: feature.Wiki
entity: Generate
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/wiki_cmd.py#run_wiki
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem wiki --out 指向已有文件时拒绝并返回 2
verify: uv run pytest tests/test_robustness.py -k wiki_out
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求复查后全部修复。
必须保持：--out 必须是目录（不存在时会创建）；指向一个已有文件时在 stderr 报一行原因、返回 2。原先拼出“文件\模块.md”的路径，抛 FileNotFoundError 异常栈。只覆盖自己生成的页面这条不变。
入口：cli/wiki_cmd.py run_wiki。
