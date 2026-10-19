---
id: 01M525TWRGYKJEKEQG0JHZC592
module: feature.Storage
entity: DirtyFiles
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/vcs/base.py#VCS
- src/pmem/vcs/git.py#GitVCS
revision: git:f778c1a
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- cheap_dirty_files
- 未提交文件清单
- svn status 慢
verified: '2026-10-19'
---
决定：版本库适配层（VCS）增加类属性 cheap_dirty_files，标明“列出未提交文件”是否便宜到可以每次调用。基类和 SVN 为 False，Git 为 True（git ls-files 走索引，几十毫秒）。

原因：SVN 的 dirty_files 要跑全量 svn status --ignore-externals --xml，大工作副本很慢（TileMatch_iLar 约 3.9 秒）。
闸门的执行前后比对是偶尔调用、且有“超过 1 秒暂停 24 小时”的保护，可以接受；
但过期核对的缓存指纹每次检索都要算，不能用慢实现。
调用方按这个属性决定要不要用 dirty_files。

影响范围：AnchorChecker 的工作区指纹只在 cheap_dirty_files 为 True 时计算；闸门的快照比对不看这个属性，SVN 仍然可用。
风险：新增版本库实现时要正确设置该属性。
