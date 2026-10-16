---
id: 01M52G7BZDS5WHBAX1GC192D17
module: feature.Storage
entity: Move
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/vcs/base.py#move
- src/pmem/vcs/svn.py#move
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- svn mv
- 移动文件
- 搬家
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：版本库适配层新增 move(src, dst)，供 pmem migrate 搬记忆文件。基类（Git、无版本库）直接移动文件并自动建目标目录，Git 提交时会识别为改名；SVN 下已纳入版本库的文件用 svn mv --parents 保留历史，未纳入的照常移动、保持未纳入（不自动 svn add）。svn mv 失败抛 OSError 带 svn 的错误输出。

原因：模块改名/合并后，记忆文件里的 module 字段必须跟着改，否则检索按新模块名过滤时找不到旧记忆（merged_into 只转发写入和模块名解析，不转发索引里已有条目）。

验证：tests/vcs/test_vcs.py 在本机 svn 下覆盖了已纳入和未纳入两种情况。风险：SVN 下搬完后源目录留空（版本化目录要 svn rm 才能删），没有自动清理。
