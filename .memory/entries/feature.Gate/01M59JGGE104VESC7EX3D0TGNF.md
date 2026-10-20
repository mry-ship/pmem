---
id: 01M59JGGE104VESC7EX3D0TGNF
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/hooks/snapshot.py#_only_committed
- src/pmem/hooks/snapshot.py#_shell_after
revision: git:edf9c94
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 误报
- 提交后提示改了文件
- 快照对比
- git commit 误判
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正：终端命令前后的未提交文件快照对比会把“提交”误判成“修改”。
现象：2026-10-19 执行 git add + git commit 后，闸门提示“刚才的终端命令改了 src/pmem/catalog/migrate.py，请立即 search_memory”，实际文件没动。
原因：变化集合按 before∪after 里状态不同的文件算，提交后文件从“未提交”列表里消失，被当成变化。
修复：文件不在 after 里、但仍存在且修改时间和大小与 before 相同时不算改动；被删掉或被 git checkout 还原（内容变了）的仍算。
