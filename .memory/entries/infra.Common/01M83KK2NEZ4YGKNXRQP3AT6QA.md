---
id: 01M83KK2NEZ4YGKNXRQP3AT6QA
module: infra.Common
entity: Roadmap
kind: correction
status: active
supersedes:
- 01M7WJ2R4EFEHAMQS899W06MCX
anchors:
- docs/superpowers/specs/2026-10-14-pmem-design.md
- README.md
- docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md
- src/pmem/core/schema.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 当前安装包是 0.7.3，勿把 --version 期望成 0.7.0
verify: uv run pmem --version
applies: 排版本或改 README/设计路线表时
source:
  kind: document
---
旧结论写「验证：pmem --version 为 0.7.0」。
0.7.0 类型安全发布仍成立，但当前安装包已是 0.7.3（工程质量、规格默认先读、reading_hint）。
排版本时以 README 路线表「当前版本 0.7.3」与功能记忆 Versioning 为准，不要再把 --version 期望成 0.7.0。
