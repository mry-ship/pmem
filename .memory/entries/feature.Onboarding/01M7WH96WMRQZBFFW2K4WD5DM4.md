---
id: 01M7WH96WMRQZBFFW2K4WD5DM4
module: feature.Onboarding
entity: Doctor
kind: feature
status: active
supersedes: []
anchors: []
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: doctor 汇总 config/modules 拼错键与 Hook 结构警告
applies: 改 doctor 输出或边界校验接入时
---
需求来源：v0.7 §3.4 doctor 汇总。

必须保持：配置/modules 拼错键与 facets 过多提示出现在 pmem doctor；Hook 字段类型不对写入 hook-errors.log，doctor 近 24 小时能看到。

适用：改 doctor 输出或边界校验接入时。
