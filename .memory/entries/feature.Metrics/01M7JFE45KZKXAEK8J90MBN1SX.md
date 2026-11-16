---
id: 01M7JFE45KZKXAEK8J90MBN1SX
module: feature.Metrics
entity: Bench
kind: decision
status: active
supersedes:
- 01M4X5ZV9ZSWY5HXJWHJXCWKCT
- 01M5CHMWGTHSPYD8R6XSD0STCB
anchors:
- src/pmem/bench/runner.py#run_bench
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 对照实验在独立工作区跑开关两组只测记忆内容；单次失败继续，仅缺开发包或密钥才整场中止
verify: pmem bench --dry-run
---
决定：pmem bench 对照实验在独立 worktree 跑；
on 复制 .memory 并内联 pmem MCP，off 清空记忆且无 MCP；
不加载 Hooks，只测记忆内容价值。
用例须先 --dry-run（起始提交验收应失败）。
单用例失败继续跑；
仅 BenchUnavailable（缺 SDK/API Key）中止整场。
Agent.create 无 mcp_servers 关键字，须放进 AgentOptions。
