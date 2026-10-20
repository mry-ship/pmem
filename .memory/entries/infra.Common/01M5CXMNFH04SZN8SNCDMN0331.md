---
id: 01M5CXMNFH04SZN8SNCDMN0331
module: infra.Common
entity: Docs
kind: decision
status: active
supersedes: []
anchors:
- README.md
- docs/pmem-guide.html
revision: git:777f86c
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 主页效果要分开列优缺点、速度、token 消耗和能省多少
verify: 打开 README 「效果」，五张表分开，上一代的下降比例在「能省多少」并写明口径
aliases:
- 效果
- token 消耗
- 能省多少
source:
  conversation: 4a38d786-a560-4c0b-9fe2-0371838dfd42
---
决定（2026-10-20，用户要求主页效果一节列清楚）：README 「效果」和手册「收益与适用场景」分开写优点和限制、速度、token 消耗、能省多少、检索有多准。
原因：原先把「端到端待实测」和检索命中、毫秒数写在同一格，读者分不清哪些已经测过、哪些只是上一代的前后对比。
分开之后，速度和 token 消耗标明本仓库实测（单次检索中位 9 毫秒，一次修 bug 约 3000～5000 token）；
被纠正下降 54%～69%、耗时下降 36%～44%、token 下降 18% 放在「能省多少」，并写明是上一代系统上线前后，不要写成 pmem 已经省下。
按文件前三写现行库的 118/120。更早记忆库副本上的 100% 只证明加分规则生效，不要写进主页。
