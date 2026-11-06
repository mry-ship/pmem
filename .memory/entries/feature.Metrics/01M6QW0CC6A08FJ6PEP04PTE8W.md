---
id: 01M6QW0CC6A08FJ6PEP04PTE8W
module: feature.Metrics
entity: Bench
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py#_git
- src/pmem/core/winproc.py#no_window_kwargs
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 消 bench 黑框勿改 MCP 为 pmemw，只藏 git/shell 子进程窗
verify: arm_options 中 MCP command 仍为 pmem
applies: Windows；pmem bench on 组
aliases:
- 黑框
- pmemw
---
排除方向：为消 bench/对照实验黑框而把 on 组 MCP 改成 pmemw（或给 MCP worker 乱加 CREATE_NO_WINDOW 掐断 stdio）。
正确做法：MCP 继续用 pmem；
只给 git worktree 与 setup/check 等 CUI 子进程加 CREATE_NO_WINDOW（core.winproc）。
与更正「bench on 组 MCP 改回 pmem serve」一致。
