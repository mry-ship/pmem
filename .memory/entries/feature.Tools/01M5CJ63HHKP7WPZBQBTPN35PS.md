---
id: 01M5CJ63HHKP7WPZBQBTPN35PS
module: feature.Tools
entity: CrossModuleSupersede
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 跨模块替代选拒绝不选警告：危害是读者看不到，警告只给写的人
aliases:
- 跨模块替代
- 替代别的模块
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
取舍：跨模块 supersedes 的危害是静默的——被替代的旧结论从原模块的检索、摘要、图谱里消失，新结论却在别的模块，查原模块的人不知道少了东西。
没选“只警告”：警告只出现在写入返回里，写的 Agent 很少回头处理，读的人仍然看不到。
没选“允许但在原模块显示指路标”：要改检索、图谱、Wiki 三处，只是缓解。
拒绝的代价小：正当需求都有替代走法（原模块写 correction；归错的先 migrate move），全库 286 条里只有 2 条跨模块替代，其中现行的 1 条就是归错模块。
风险：一条新结论同时推翻两个模块的记忆时，要在每个模块各写一条。
