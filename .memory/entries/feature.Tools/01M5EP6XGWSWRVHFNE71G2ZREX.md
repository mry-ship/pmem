---
id: 01M5EP6XGWSWRVHFNE71G2ZREX
module: feature.Tools
entity: SupersedeLineage
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/record.py#_record
- src/pmem/metrics/health.py#_cross_module_supersedes
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 跨模块替代只放开给下级模块，不放开祖先：被替代的记忆会从它自己模块的检索消失
aliases:
- 跨模块替代
- 提升到父模块
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
决定：父子模块后 supersedes 只放宽到“本模块或下级模块的记忆”，不允许子模块替代父模块（或更上级）的记忆。设计稿原写“直系之间都可替代”，实现时收紧。
原因：被替代的记忆会从它所在模块的检索中隐藏。
父模块的教训会被所有下级继承，如果 system.Ads.Max 替代了 system.Ads 的教训，AdMob、Yandex 等兄弟模块也再也看不到那条结论，等于一个子模块悄悄改了全体的结论。
反方向是安全的：把子模块的教训提升到父模块并替代它，子模块仍能通过继承看到新结论。
子模块确实发现父模块结论不对时：在父模块写 correction 替代（结论适用于全体），或在子模块写一条带 applies 的例外说明。
health 的跨模块替代检查同样把“替代下级”排除在外。
