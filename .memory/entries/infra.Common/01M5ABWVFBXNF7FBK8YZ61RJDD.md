---
id: 01M5ABWVFBXNF7FBK8YZ61RJDD
module: infra.Common
entity: Roadmap
kind: decision
status: active
supersedes: []
anchors:
- docs/superpowers/specs/2026-10-14-pmem-design.md
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 版本规划
- 路线图
- v0.3
- roadmap
- RemoteStorage 顺延
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
决定（2026-10-19）：v0.3 的范围从“RemoteStorage 中心服务、权限、审计、看板”改为“记忆质量与上下文效率”，中心服务顺延到 v0.4+（并入团队汇总）。
任务清单与验收标准在设计文档 docs/superpowers/specs/2026-10-14-pmem-design.md 第 14.2 节。

原因：本仓库实测记忆库在变成变更日志（决定占 65%、排除项仅 2 条）、采用率 19%、对话内重复返回 40%（证据见 feature.Curation/CorpusQuality），先把“记什么、怎么喂给 AI”做对，团队化才有意义。

v0.3 六项：写入改为“有教训才写”并修复变更记录检测；对话内去重；一行标题 summary；全项目级坑 scope: project；可选验证方法 verify；验收度量（真实 bench、类型占比、重复返回率）。
明确不做：按采用率调排序（只在本机、离线计算，会让不同人检索结果不一致）；强制两段式检索（多一次往返变慢）。

风险：“有教训才写”可能让写入量下降，需用类型占比（排除项+风险+更正 ≥ 30%）和结束提醒转化率监控。
