---
id: 01M5CAW2W30BN2GJ03ENRHNT4K
module: infra.Common
entity: CLI
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
- src/pmem/cli/brief.py#_search
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 命令行支持 feature 类型、applies 与按 id 取全文，简报单列功能记录
aliases:
- 命令行
- 按id取全文
- 适用条件
---
用户要求（2026-10-19）：命令行也要能写功能记录、按 id 取全文。
必须保持：record 的 --kind 选项直接取 core/entry.py 的 KINDS（不再手写一份），新增 --applies；
search 新增 --id（可跟多个）。
--brief 输出里功能记录单列一组（“功能记录与规划 N 条”），带 applies 的行下面加“适用：…”，并显示 applies_hint 和 missing。
入口：cli/main.py 的 build_parser、SERVICE_COMMANDS；cli/brief.py 的 _search。Wiki 页面在正文后显示“适用条件”（generate/wiki.py）。
