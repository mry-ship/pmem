---
id: 01M5A0PEWG6WSEJXC1SNZFGPD0
module: feature.Onboarding
entity: Init
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/integrations.py#setup_cursor
- src/pmem/cli/init_cmd.py#run_init
revision: git:4e8ab24
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 接入
- integrations
- init 合并
- hooks.json 合并
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：init 里各家 Agent 的接入逻辑移到 src/pmem/generate/integrations.py：pick_agents、合并 hooks.json / Claude settings.json / mcp.json / .codex/config.toml、CLAUDE.md/AGENTS.md 段落、包装脚本、技能、setup_cursor/claude/codex 与 NEXT_STEPS。
cli/init_cmd.py 只剩 guess_type 和 run_init（建 config.yaml、modules.yaml、打印结果）。
原因：合并逻辑与命令行解析无关，doctor 等以后要复用时不必从 cli 导入（issue #11）。
影响：行为不变，全量测试通过；
modules.yaml 把 integrations.py 登记到 feature.Onboarding（否则按 src/pmem/** 落到 infra.Common）；
指向 init_cmd.py#merge_hooks/#write_hook_wrappers/#_write_skills 的 4 条记忆已用 anchors --rename 改到新文件。
