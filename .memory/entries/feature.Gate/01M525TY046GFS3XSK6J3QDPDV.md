---
id: 01M525TY046GFS3XSK6J3QDPDV
module: feature.Gate
entity: ShellSnapshot
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell.py#may_change_unseen
- src/pmem/hooks/gate.py#Gate._dirty_snapshot
revision: git:f778c1a
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 执行前后比对
- 快照慢
- svn 只读命令
- 终端卡顿
verified: '2026-10-19'
---
结论：SVN 工作副本上终端命令的执行前后比对有两处多余开销，已去掉。

1. svn 只读子命令（status/st、log、diff/di、info、cat、list/ls、blame/praise/annotate、propget、proplist、help）被当成“不认识的程序”，每次都触发前后两次全量 svn status。
   现在与 git 只读子命令一样直接放行，不做比对；
   svn update、revert、commit 等仍会比对。
2. 执行前快照本身就超过 1 秒时，原先会写暂停标记但仍保留这次快照，执行后还要再跑一遍全量扫描（TileMatch 实测前后各约 3 秒）。现在执行前就慢则直接放弃这次比对，只付一次代价，之后 24 小时暂停快照。

证据：TileMatch_iLar 模拟 Hook，svn log -l 1 从前后各约 3.1 秒降到 0.17 秒；未知脚本第一次执行前约 3.1 秒、执行后 0.18 秒，第二次起均约 0.17 秒。

影响范围：第 2 点让“暂停前的最后一次”命令也不做事后比对，这一次通过终端改的文件闸门看不到；属于已有“慢就暂停”取舍的延伸。
