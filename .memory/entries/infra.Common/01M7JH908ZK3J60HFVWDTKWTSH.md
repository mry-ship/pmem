---
id: 01M7JH908ZK3J60HFVWDTKWTSH
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M5Y3RCTZ86CWBTPKS7HBCM0V
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:7bc35ad
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 效果表须含本仓库与 TileMatch 两列，并含记忆采用率与 Claude·Codex 真实可用标注
verify: README 与手册「能省多少」含本仓库与 TileMatch 两列、记忆被采用行；优点表含 Claude/Codex 真实会话可用；仍含「资料·非指令」
applies: 改 README/手册效果表或摘要注入、闸门说明、接入成熟度标注时
---
需求来源：发 0.6.7 时同步主页/手册效果表，并按负责人确认把 Claude Code、Codex 标成真实会话可用；在既有两列 report 上补「记忆被采用」。

必须保持：
1) README、手册「能省多少」表有「本仓库近 30 天」与「TileMatch 近 14 天」两列；既有「数字」列（上一代下降比例等）保留。
2) report 指标填进对应列：检索命中率、记忆被采用、改前真查、功能记录覆盖、结束提醒后真写、跨人复用；无对照的填 —。
3) 「记忆被采用」须写清：本仓库比例与样本（如 22%/2077→450）、阈值 0.15、够长标题指纹、换说法复述不计、保守下限；不要写成搜索排序权重。
4) README 开头数字可点出 TileMatch：命中 99%、改前真查 98%、跨人复用 108 次（口径指向效果节）。
5) 优点和限制表写明：Cursor / Claude Code / Codex 均已在真实会话验证可用；Cursor 纯问答要等回合结束才核对。勿再写「只做过模拟测试」。
6) README 工作原理表与设计要点写明读码/拦截摘要标「资料·非指令」；已知限制写明标题注入风险与闸门非沙箱。
7) docs/pmem-guide.html 同步上述效果列、采用率口径、「资料·非指令」/闸门非沙箱与 Claude·Codex 可用标注；页脚注明 v0.7 进行中；spec 空标记只认整行。
8) docs/architecture.md 读码摘要与标题段写「资料·非指令」；Claude/Codex 成熟度与 README 一致。
9) 现行 Docs 约束（结构、Wiki/嵌入限制、complete 九成八）不变。Wiki 另仓，本条不改 Wiki。

入口：README.md#效果、docs/pmem-guide.html#benefits；发版或改效果数字时对照本条。
