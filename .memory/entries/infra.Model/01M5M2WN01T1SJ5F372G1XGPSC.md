---
id: 01M5M2WN01T1SJ5F372G1XGPSC
module: infra.Model
entity: Config
kind: correction
status: active
supersedes:
- 01M5KV8RKHXECTCNT15TBNBWMJ
anchors:
- src/pmem/core/config.py
revision: git:6096f71
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: spec.reminder 缺省关闭；文件里写成 true 的仍提醒
verify: uv run pytest tests/core/test_config.py -q -k spec_reminder
applies: 读取没有 spec.reminder 的 config.yaml 时；新项目 pmem init 生成的配置模板
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
更正：spec.reminder 缺省改为关闭。spec.dir 仍默认 .memory/specs。
原因：回合结束的规格跟进会当成下一条用户消息，一轮改了多个模块时代理会当着用户面去补规格，用户要求默认无感。
读取时仍与默认值合并：磁盘上没写 spec.reminder 的旧项目，升级后不再弹出规格提醒；只写了 spec.dir 时 reminder 仍取 false。文件里已经写成 true 的仍提醒。
init 不回写已有 config.yaml。新项目模板里这一行也是 false。
不变：记忆检索、功能记录提醒（gate.stop_reminder）、只查了记忆的提醒（gate.analysis_reminder）、闸门默认 block，都不因这一项关掉。
