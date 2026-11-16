---
id: 01M7JHJFZ4YR2E3N7Q8J0QZ9KE
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M7JH908ZK3J60HFVWDTKWTSH
anchors:
- README.md
- docs/pmem-guide.html
revision: git:7bc35ad
author: 1002378395@qq.com
note_date: '2026-11-17'
summary: 效果栏须有当前版本小节：0.6.7 采用率等口径与 Claude·Codex 真实可用
verify: README 与手册含「当前版本 0.6.7」表且采用行写 22%/旧约 13%
applies: 改 README/手册效果表或发版同步效果数字时
---
需求来源：用户指出效果栏没写当前版本效果内容；补「当前版本 0.6.7」小节并刷新本仓库近 30 天数字。

必须保持：
1) README「效果」与手册「收益与适用场景」开头有「当前版本 0.6.7」表：命中率、记忆被采用（含旧正文口径约 13%→现行 22% 与「未降阈值/未按采用排序」说明）、改前真查、功能记录覆盖、结束提醒后真写、防错类占比、Claude/Codex 真实会话可用。
2) 「能省多少」表本仓库列与当前 report 对齐（命中、采用、真查、覆盖、真写、跨人复用）；注明 0.6.7 口径。
3) README 关键数字含本仓库近 30 天：命中、采用、改前真查。
4) 既有两列 report（本仓库 / TileMatch）、上一代「数字」列、「资料·非指令」、闸门非沙箱、Wiki 另仓等 Docs 约束不变。

入口：README.md#效果、docs/pmem-guide.html#benefits。
