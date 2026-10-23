---
id: 01M5KV8RKHXECTCNT15TBNBWMJ
module: infra.Model
entity: Config
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 旧配置读取时并入 spec.dir 与 spec.reminder，缺省就提醒
applies: 读取没有 spec 段的旧 config.yaml 时
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
决定：spec.dir 默认 .memory/specs，spec.reminder 默认开。旧配置文件不必手改，读取时与默认值合并；文件里已经写了 spec.dir 的，沿用那个值。
原因：和 wiki.auto 一样，升级后不用每个人改配置就会开始提醒。init 不回写已有 config.yaml，所以磁盘上的旧文件可以没有 spec 段。
