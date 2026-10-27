---
id: 01M5CQ77AS6WHSJTE9XFB05TMH
module: feature.Onboarding
entity: Init
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/integrations.py#upsert_block
- src/pmem/generate/integrations.py#merge_group_hooks
- src/pmem/generate/integrations.py#pick_agents
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 重跑 init 不吞用户内容、不留旧 Hook；doctor 配置写错给 ✘，有提醒不说一切正常
verify: uv run pytest tests/test_integrations.py
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺，审查复现出接入合并和自检的问题。
必须保持：
1. CLAUDE.md / AGENTS.md 里 pmem 段落的结束标记被删时，重跑 pmem init 只去掉孤立的开始标记并追加新段落，用户写的内容一字不少。
2. Claude Code / Codex 的 Hook 合并和 Cursor 一样：模板里已经没有的事件下，残留的 pmem 处理器也删掉，别家处理器保留。
3. hooks 不是“事件名 → 列表”时以 SystemExit 给出可读原因；--agents "," 这种空列表同样报错。
4. pmem doctor：config.yaml 写错时显示 ✘ 和原因并返回 1，不抛异常栈；有 ! 提醒时结尾说“有 N 项提醒”，不再说“一切正常”。
5. 收口技能和 health 里按议题拆模块的示例写全 --to <新模块>=<议题>，原示例缺必填的 --to，照做会报错。
入口：generate/integrations.py、cli/doctor_cmd.py、generate/templates.py。
