---
id: 01M63Y9HERN41S7QG1V7PVQ2G5
module: feature.Metrics
entity: TileMatchReport
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py
- src/pmem/vcs/svn.py#uncommitted_count
revision: git:a1627f5
author: 1002378395@qq.com
note_date: '2026-10-29'
summary: TileMatch 表上真正不够的是未提交、采用10%、排查收口转化，不是99%命中
verify: 本机 events.jsonl 跨度约13天；svn status --xml .memory/entries 的 item=added
aliases:
- 采用率
- 未提交
- 90天同左
---
TileMatch 这份 30/90 天收益表，不够的不在命中率。2026-10-29 本机日志只有 13.1 天（10-16～10-29），所以检索/采用/避坑/新写习惯在 90 天窗几乎「同左」，不是业务稳定，是事件日志不够长。

按缺口大小：
1) 未提交 1340：.memory/entries 全部是 svn added、从未提交（status xml 1399 条 added）。
   有效 672 条队友也看不到。
   报告里的「跨人复用 161」几乎全是 author=imported，不是同事在用。
2) 采用 49/508（10%）：字面重合下限，但结合检索 262/260（99%）说明「总能搜到东西」≠「用上了」。无相关度阈值（见 Retrieval/Ranking 排除项），结论库把结果撑满，Agent 复述很少。
3) 防错类 8%/6%：分母含导入 conclusion，本机 10-19 后已 32.5%（见 PitfallShare）。
4) 排查收口仍漏：analysis_reminder 已开，19 个排查对话里 11 个最后一次 stop 仍有 analyzed（17 个模块）；结束催写 34 次只转化 20 次。开关不是瓶颈，转化才是。
5) 功能记录覆盖 20/23（87%）只有 9 个对话的 required，样本脆；本机 feature 一共 34 条。
6) 登记 80 个模块 22 个空；现行 672、被替代仍 active 的 668 条和未提交绑在一起膨胀。
7) 「期前从未被检索 117」被 13 天日志放大；90 天窗盖住全部记忆后这一节消失，不代表都有人用。

验证：本机 events.jsonl 跨度约 13 天；svn status --xml .memory/entries 的 item=added。
