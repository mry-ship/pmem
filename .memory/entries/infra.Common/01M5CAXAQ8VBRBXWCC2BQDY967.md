---
id: 01M5CAXAQ8VBRBXWCC2BQDY967
module: infra.Common
entity: Roadmap
kind: decision
status: active
supersedes:
- 01M5ABWVFBXNF7FBK8YZ61RJDD
anchors:
- docs/superpowers/specs/2026-10-14-pmem-design.md
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 路线记在设计文档第 14 节和 GitHub Issue 12-14，v0.3.1 已实现
aliases:
- 版本规划
- 路线图
- roadmap
- v0.3.1
- v0.3.2
- v0.4
---
决定（2026-10-19 更新路线）：路线记录在设计文档第 14 节和 GitHub Issue（mry-ship/pmem #12 v0.3.1、#13 v0.3.2、#14 v0.4），进度以 Issue 勾选为准。
- v0.3（已发布）：记忆质量与上下文效率，一行标题、对话内去重、全项目级坑、verify、验收度量（14.2）。
- v0.3.1（已实现）：功能记录 feature 与教训分层检索、模块教训摘要、applies、plan、免记录文件、合并不跨条件、覆盖率度量（14.3）。
  用户要求做功能也要落库，否则用户要求的行为会被后来的 AI 改回去；
  v0.3 的“有教训才写”因此改为“改了模块写功能记录，有教训另写”。
- v0.3.2：记忆图 pmem map（演化过程与漏记、断链、悬而未决、过期自检）、合并回滚、跳过复查、严格的清理候选（只归档、人确认，14.4）。
- v0.4+：自动新建模块转正提示、召回审计建议、RemoteStorage 中心服务与团队汇总；模块依赖图以后评估。
不借鉴：相关度阈值、时间衰减打分、大模型判断模块归属、存原始对话、后台自动改写记忆、提问时注入（理由见 14.4）。
仍有效：不按采用率调排序（只在本机离线计算，会让不同人检索结果不一致）；不强制两段式检索。
