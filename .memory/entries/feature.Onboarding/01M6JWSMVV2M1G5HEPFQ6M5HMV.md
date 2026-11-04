---
id: 01M6JWSMVV2M1G5HEPFQ6M5HMV
module: feature.Onboarding
entity: Init
kind: decision
status: active
supersedes:
- 01M5A0PEWG6WSEJXC1SNZFGPD0
anchors:
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/init_cmd.py#run_init
revision: git:cef5279
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: 各 Agent 接入在 integrations.py；init 只调 setup_* 合并配置
verified: '2026-11-04'
verified_at: '2026-11-04T17:04:24.128+08:00'
---
决定：init 里各家 Agent 的接入逻辑移到 src/pmem/generate/integrations.py：pick_agents、合并 hooks.json / Claude settings.json / mcp.json / .codex/config.toml、CLAUDE.md/AGENTS.md 段落、包装脚本、技能、setup_cursor/claude/codex 与 NEXT_STEPS。
cli/init_cmd.py 只剩 guess_type 和 run_init（建 config.yaml、modules.yaml、打印结果）。
原因：合并逻辑与命令行解析无关，doctor 等以后要复用时不必从 cli 导入（issue #11）。
影响：行为不变，全量测试通过；
modules.yaml 把 integrations.py 登记到 feature.Onboarding（否则按 src/pmem/** 落到 infra.Common）；
指向 init_cmd.py#merge_hooks/#write_hook_wrappers/#_write_skills 的 4 条记忆已用 anchors --rename 改到新文件。
