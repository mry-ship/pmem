---
id: 01M63YRCXE5JY2WGJPQS271Z0R
module: feature.Metrics
entity: CiteConversion
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/cite.py#judge
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/metrics/report.py
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: 采用低是查过不用；防错少是先写feature；催写约60%两边一样
verify: uv run pmem report --days 30；uv run pmem report --days 30 --root <TileMatch>
aliases:
- 采用率
- 催写转化
- 防错类
---
对照本仓库与 TileMatch 的 pmem report（同机 30 天），采用低、防错少、催写转化约 60% 是同一套机制，不是 TileMatch 特例。

采用（TM 10% / 本仓库 17%）：不是阈值略严那么简单。
TM 508 条里 282 条分数 <0.05（55% 连词都没沾上），177 条 0.05–0.15 近失；
本仓库 <0.05 只有 33%。
闸门逼的是「查过就能改」，不逼「用上」。
模块检索把同模块热门结论反复塞进结果（infra.Framework/LocalNotificationFocusLog 同模块命中 22 次从未采用）。
防错类采用更差：TM exclusion 0/10、risk 6%、correction 5%。
本机作者采用 6.1% 低于 imported 12.2%，导入长文和游戏常用 4 字更容易碰巧撞上回复。
判定只看可见回复正文，改代码用了也不算；
但过半 <0.05 说明多数是真没用，不是换了说法。

防错（TM 全库 8% / 本机教训 21.5% / 本仓库 29%）：本仓库接近 30% 是因为 60 条 correction（产品自己在推翻旧结论），exclusion 也只有 12 条。
TM 本机 219 条里 conclusion+decision 占 78%。
结束提醒先逼 feature，「另有以下内容才写教训」；
排查文案允许 conclusion 交差；
compact 默认 conclusion。
导入 1087 条里防错 2.7% 把全库拉到 8%，但即便只看本机也没到 30%。

催写转化（TM 20/34=59%，本仓库 27/42=64%）：两边一样差。
TM 14 次未转化里 8 次来自同一长对话 35aebaa9（70 次 stop）：其中 infra.Debugger 写 feature 被旧 MCP 拒绝（kind 当时还没有 feature，见 Tools/Layered「升级要重启服务」）；
其余是隔天再催已写过的模块，转化口径要求「这次 stop 之后再写一次」。
另 2 次 system.Objective 只有 1 轮，用户没续跑 followup。
排查类催了之后 Agent 写了别的模块，analyzed 仍留在最后一次 stop。
声明「无新结论」不算转化。
