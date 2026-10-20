---
id: 01M5CE9DHEA1Z99KKJ7SE5WKEZ
module: feature.Metrics
entity: ModuleAudit
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/audit.py#promotion_hints
- src/pmem/metrics/audit.py#recall_audit
revision: git:d6b5bd7
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: health 给未登记模块建议 paths，并列出召回偏低的模块（只看教训）
aliases:
- 转正
- 召回审计
- 查不出来
---
需求来源：用户要求 v0.4 先做治理闭环的前两项（GitHub Issue #14）：自动新建模块的转正提示、召回审计建议。
必须保持的行为：
- pmem health 的“未登记模块”按记忆的关联代码给建议登记的 paths（同目录 2 个以上文件登记整个目录，否则单个文件，最多 5 条），并列出这些代码现在归哪个模块；
  没有关联代码时说明推断不出；
  冷候选提示 pmem sync --apply 转正。
  只建议，不自动改 modules.yaml。
- 新增“召回偏低”一节：本机成功检索不少于 20 次时才统计；
  现行教训不少于 10 条、按模块检索不少于 10 次、被返回过的教训不到 30% 的模块列出，附从没返回的议题（前 3 个）；
  议题不少于 8 个时提示可拆模块。
  已废弃、已并入的模块不列。
- 只统计教训：功能记录在检索里只给标题，不进 search 事件的 ids，算进来会让所有模块都显得召回偏低。
- 本仓库上线时各模块被返回过的教训占 67%～100%，不触发；阈值面向 TileMatch 这类大模块。
入口：src/pmem/metrics/audit.py 的 promotion_hints、recall_audit。
