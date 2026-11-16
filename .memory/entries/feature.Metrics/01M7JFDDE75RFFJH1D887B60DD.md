---
id: 01M7JFDDE75RFFJH1D887B60DD
module: feature.Metrics
entity: Bench
kind: feature
status: active
supersedes:
- 01M5CVMTAKXTXWWAYBZNDMK4GB
- 01M6QW0A54E9BSBYVEZZAF3QP5
anchors:
- src/pmem/bench/runner.py#run_bench
- src/pmem/bench/runner.py#_git
- src/pmem/core/winproc.py#no_window_kwargs
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: bench：独立工作区对照开关两组；单例失败继续；无窗仅藏命令行；记忆服务仍用本命令
verify: uv run pytest tests -k bench; pmem bench --dry-run
applies: 跑 pmem bench / 对照实验
---
需求来源：pmem bench 对照实验与 Windows 无黑框验收。
必须保持：
1) 每次运行在独立 git worktree，从用例指定提交开始；
   on 组复制当前 .memory、内联 pmem MCP（AgentOptions.mcp_servers），并把 pmem 规则作提示词前缀；
   off 组清空 entries 且不给 MCP。
   两组都不加载项目/用户设置（SDK 默认 setting_sources 为空），不触发 Hooks，测的是记忆内容本身。
2) Agent 结束后才把 check_files 放进工作区执行验收；MCP 子进程带 PMEM_NO_EVENTS=1，不污染个人报告。
3) 单次运行出错记 status=error 并继续；
   只有缺 Cursor SDK / 未设 CURSOR_API_KEY（BenchUnavailable）时整实验中止，命令行打原因返回 2。
   git 失败等不得用裸 RuntimeError 冒充全局中止。
4) --dry-run：用例 status 不是 dry_run、起始提交上验收已通过、或一个用例都没跑时返回 1 并分别列出；须先 dry-run 验证用例有效。
5) --arms 只能 on/off；用例文件不存在、顶层不是键值对、cases 不是列表时返回 2，不打异常栈。
6) Windows 上建/删 worktree、跑 setup 与验收时 subprocess 一律带 CREATE_NO_WINDOW（core.winproc.no_window_kwargs）；
   on 组 MCP 仍用 pmem serve，不用 pmemw。
入口：cli/main.py _bench；bench/runner.py load_cases / run_bench / _git / run_check。
