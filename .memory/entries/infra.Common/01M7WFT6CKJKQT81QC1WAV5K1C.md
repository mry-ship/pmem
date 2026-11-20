---
id: 01M7WFT6CKJKQT81QC1WAV5K1C
module: infra.Common
entity: Versioning
kind: feature
status: active
supersedes:
- 01M7JH0Q8Y35AFG00Y9NZ0694T
anchors:
- README.md
- docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: v0.7 阶段1已落地 enforced_by 与规则候选；安装包仍 0.6.7 不跳号
verify: rg enforced_by src/pmem/core/entry.py；README 路线表含 enforced_by
applies: 发版或改路线表当前版本时
---
需求来源：落地 v0.7 阶段 1（规则化）但不发版号跳到 0.7.0。
必须保持：安装包仍为 0.6.7 补丁线，直到阶段收齐再发 0.7.0；
README 路线表写明已落地 schema、enforced_by、health 可写成规则。
入口：README 路线表；
设计稿 2026-10-21-pmem-typesafe-design.md。
