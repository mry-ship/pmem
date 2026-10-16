---
id: 01M525TV4DF1JDYWBBRR6TT6X8
module: feature.Retrieval
entity: StaleCheck
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#AnchorChecker._worktree_state
revision: git:f778c1a
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 过期核对缓存
- 指纹
- 检索慢
- 摘要慢
- svn status 慢
---
决定：过期核对（AnchorChecker）的跨进程缓存只在“列未提交文件便宜”的版本库上启用（目前只有 Git）；SVN 不算工作区指纹、不用 anchors.json 缓存，照旧只核对本次选中记忆的锚点。

原因：缓存要用工作区指纹（版本 + 日期 + 每个未提交文件的修改时间和大小）判断代码有没有变，指纹靠 vcs.dirty_files()。
给 SVN 实现 dirty_files（供闸门执行前后比对）以后，指纹也开始在 SVN 上跑全量 svn status。
TileMatch_iLar 实测一次约 3.9 秒（1845 条状态），每次读代码摘要、每次检索都要付一遍：读代码摘要从约 0.3 秒变成 3.4 秒。

做法：版本库适配层加类属性 cheap_dirty_files（基类 False，Git True），指纹只在为 True 时调用 dirty_files。修复后 TileMatch 读代码摘要回到 0.27 秒。

影响范围：Git 仓库行为不变；SVN 仓库每个新进程都重新核对选中的锚点（与 dirty_files 出现之前一致，单次核对只查少量文件，快）。
风险：以后新增版本库适配时，如果 dirty_files 很快，记得把 cheap_dirty_files 设成 True，否则享受不到缓存；反过来把慢的设成 True 会让每次检索都变慢。
