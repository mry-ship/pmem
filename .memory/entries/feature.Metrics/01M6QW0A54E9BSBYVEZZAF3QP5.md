---
id: 01M6QW0A54E9BSBYVEZZAF3QP5
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py#_git
- src/pmem/bench/runner.py#run_check
- src/pmem/core/winproc.py#no_window_kwargs
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: bench 调 git/setup/check 时 Windows 必须 CREATE_NO_WINDOW
verify: grep no_window_kwargs in src/pmem/bench/runner.py; pytest tests/test_layering.py
  -q
applies: Windows；pmem bench
aliases:
- 黑框
- CREATE_NO_WINDOW
---
需求来源：用户要求不改闸门功能、只消 Windows 黑框；复查发现 bench 仍裸调 git/setup/check。
必须保持：bench 建/删 worktree、跑 setup 与验收命令时，Windows 上 subprocess 一律带 CREATE_NO_WINDOW（经 core.winproc.no_window_kwargs）；
on 组 MCP 仍用 pmem serve（不用 pmemw）。
适用：Windows 上跑 pmem bench。
入口：bench/runner.py 的 _git、remove_workspace、run_check、setup 调用。
