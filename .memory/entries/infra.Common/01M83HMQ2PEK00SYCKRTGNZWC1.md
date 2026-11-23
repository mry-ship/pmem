---
id: 01M83HMQ2PEK00SYCKRTGNZWC1
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M83GZNYE10D3B0C9GBMXZ1N6
anchors:
- docs/architecture.md
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: architecture、手册与 README 已对齐 0.7.3 与二次放行口径
verify: architecture 文首含 0.7.3；指南含记忆闸门优先与再改放行；设计稿与 README 路线表不含规格提醒默认不提示
applies: 改 README/手册/架构/设计路线或发版同步时
source:
  kind: document
---
需求来源：0.7.3 发版后 architecture 与设计稿路线表未对齐；手册效果表少写记忆闸门优先，且把 block 写成「读完才放行」；README 路线表 v0.6 仍写规格提醒默认不提示。

必须保持：
1) docs/architecture.md 文首写明当前安装包 0.7.3 增量（工程质量技能、规格默认先读、reading_hint、source.kind/valid_from、spec closed、记忆闸门优先与二次放行口径）。
2) 设计稿 §14 路线表含 v0.7.2 / v0.7.3 行；§14.7 注明后续补丁；v0.6 行不再写「规格提醒默认不提示」与现行矛盾。
3) docs/pmem-guide.html 的 v0.7.3 能力行含「记忆闸门优先于规格闸门」；spec 命令说明写明 block 摘录后再改放行的前提。
4) 模块规格设计稿写明二次放行与已读只认成功 Read。
5) README 路线表 v0.6 行写明规格提醒后来在 0.7.3 改为默认开启。
6) Wiki 仍另仓，本条不保证 Wiki 已推。

适用：改 README/手册/架构/设计路线或发版同步时。
