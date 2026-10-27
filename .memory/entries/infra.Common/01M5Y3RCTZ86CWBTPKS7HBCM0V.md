---
id: 01M5Y3RCTZ86CWBTPKS7HBCM0V
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M5Y3EF63GAXWVA06CG7S01BW
anchors:
- README.md
- docs/pmem-guide.html
revision: git:651fca2
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 效果「能省多少」须有本仓库与 TileMatch 两列 report；资料·非指令等说明不变
verify: README 与手册「能省多少」含本仓库与 TileMatch 两列及跨人复用行；仍含「资料·非指令」
applies: 改 README/手册效果表或摘要注入、闸门说明时
aliases:
- 效果表
- TileMatch 报告
- 近30天列
- pmem report 主页
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：用户要求效果表用 pmem report 补列，并补上真实案例 TileMatch 报告，不替换既有离线/上一代数字。
必须保持：
1) README、手册「能省多少」表有「本仓库近 30 天」与「TileMatch 近 14 天」两列；
   既有「数字」列（上一代下降比例等）保留；
   report 指标（命中率、改前真查、功能记录覆盖、结束提醒后真写、跨人复用）填进对应列，无对照的填 —。
2) README 关键数字可点出 TileMatch：命中 99%、改前真查 98%、跨人复用 108 次（口径指向效果节）。
3) README 工作原理表与设计要点写明读码/拦截摘要标「资料·非指令」；已知限制写明标题注入风险与闸门非沙箱。
4) docs/pmem-guide.html 同步上述效果列与「资料·非指令」/闸门非沙箱；页脚注明 v0.7 进行中；spec 空标记只认整行。
5) docs/architecture.md 读码摘要与标题段写「资料·非指令」。
6) 现行 Docs 约束（结构、Wiki/嵌入限制、complete 九成八）不变。
Wiki 另仓，本条不改 Wiki。
入口：README.md#效果、docs/pmem-guide.html#benefits。
