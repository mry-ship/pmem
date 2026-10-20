---
id: 01M5CE9P6WRABMA9NPPSPBB50S
module: infra.Common
entity: Roadmap
kind: decision
status: active
supersedes:
- 01M5CAXAQ8VBRBXWCC2BQDY967
anchors:
- docs/superpowers/specs/2026-10-14-pmem-design.md
revision: git:d6b5bd7
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: v0.4 先做转正提示和召回审计；团队汇总走导出文件进仓库，中心服务暂缓
---
决定（2026-10-20 更新路线）：v0.4（GitHub Issue #14）只做前两项，团队汇总和中心服务暂缓。
- 已实现：pmem health 的未登记模块转正提示、召回审计（见 feature.Metrics / ModuleAudit与设计文档 14.5）。
- 团队汇总方向由用户选定：不搭中心服务，各人把本机统计导出成文件提交到仓库、负责人汇总，零运维；要解决隐私（不带检索原文、对话 id）、按人分文件避免冲突、口径与单机 report 一致。
- RemoteStorage 中心服务、身份与权限、审计、看板：等文件方案用起来、确认需要实时共享后再设计。
- v0.3.1、v0.3.2 均已实现（Issue #12、#13 已全部勾选）。
仍有效：路线记在设计文档第 14 节和 GitHub Issue，进度以 Issue 勾选为准；不借鉴的方向见 14.4。
