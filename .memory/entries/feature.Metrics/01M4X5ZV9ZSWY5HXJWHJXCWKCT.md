---
id: 01M4X5ZV9ZSWY5HXJWHJXCWKCT
module: feature.Metrics
entity: Bench
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/bench/runner.py#run_bench
revision: git:74edc08
author: 1002378395@qq.com
note_date: '2026-10-14'
---
pmem bench 对照实验的设计：每次运行在独立 git worktree 中从用例指定的提交开始；
on 组复制本仓库当前 .memory（模拟前人已踩过坑）并内联 pmem MCP 服务、把 pmem 规则作为提示词前缀；
off 组清空 entries 且不给 MCP。
两组都不加载项目/用户设置（SDK 默认 setting_sources 为空），因此不触发 Hooks，测的是“记忆内容本身”的价值。
Agent 结束后才把 check_files 隐藏验收放进工作区并执行 check。
MCP 子进程带 PMEM_NO_EVENTS=1，不污染个人报告。

用例有效性必须先用 pmem bench --dry-run 验证：不调用 Agent，起始提交上验收应失败。
示例用例 gate-guidance（提交 e258c6e）在起始提交上隐藏验收失败、原有 50 个测试通过，当前 HEAD 能通过。

注意：cursor_sdk 的 Agent.create 没有 mcp_servers 关键字参数，必须放进 AgentOptions(mcp_servers=...)；尚未用真实 API Key 跑过完整对照。
