---
id: 01M5M38K4M36HGFDS81Z1J2HJY
module: feature.Onboarding
entity: Init
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/init_cmd.py#choose_spec_reminder
revision: git:dabf9c4
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 首次 init 在终端里问要不要开规格提醒，回车保持关闭
verify: uv run pytest tests/test_cli_flow.py -q -k spec_reminder
applies: pmem init 首次生成 config.yaml 时
aliases:
- 规格提醒
- spec.reminder
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户要求：规格提醒默认可以不开，但接入时要问一声，开不开由使用者决定。
必须保持：只在还没有 config.yaml 时询问。终端里输入 y 才把 spec.reminder 写成 true，直接回车保持 false。没有终端时不询问、不阻塞，保持关闭并打印改法。
已有配置再跑 init 不再问，也不改这一项。
入口：pmem init。
