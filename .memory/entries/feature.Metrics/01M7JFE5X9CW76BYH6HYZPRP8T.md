---
id: 01M7JFE5X9CW76BYH6HYZPRP8T
module: feature.Metrics
entity: Bench
kind: exclusion
status: active
supersedes:
- 01M6JKMACSHVEF54SZJR4CKDXD
- 01M6QW0CC6A08FJ6PEP04PTE8W
anchors:
- src/pmem/bench/runner.py#_git
- src/pmem/core/winproc.py#no_window_kwargs
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: bench 消黑框时排除改用包装命令或给记忆服务窗口加无窗，只藏命令行子进程
verify: rg pmemw src/pmem/bench
applies: Windows 上消 bench 黑框时
---
排除：为消 bench 黑框而把 on 组 MCP 改成 pmemw，或给 MCP worker 加 CREATE_NO_WINDOW 掐断 stdio。
MCP 继续用 pmem；
只给 git worktree 与 setup/check 等 CUI 子进程加 CREATE_NO_WINDOW（core.winproc）。
