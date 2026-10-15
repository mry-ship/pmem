---
id: 01M4XFGPBBEE838VGRFE9V7WWG
module: feature.Storage
entity: Uncommitted
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/vcs/svn.py
- src/pmem/vcs/git.py
revision: git:4e837a8
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-15'
---
风险：统计“本机未提交的记忆数”时，SVN 下如果 .memory 目录本身还没加入版本库，`svn status --xml <.memory/entries>` 只输出 W155010“找不到节点”警告，退出码仍为 0，返回的 XML 也没有任何 entry，计数就会是 0。也就是说，“刚接入、一条都没提交”这种最需要提醒的情况反而不提醒。

处理：先用 `svn info` 判断目录是否已纳入版本库；没纳入时，其中的 .md 全部算未提交。已纳入时再看 status：unversioned、added、modified、replaced 都算未提交，未纳入版本库的子目录递归统计其中的 .md。

Git 侧用 `git status --porcelain --untracked-files=all -- <目录>`，必须带 --untracked-files=all，否则新模块目录只显示为一行目录，计数会偏少。

验证：tests/vcs/test_vcs.py 覆盖了 git 和 svn 两种情况，包括目录整个未纳入、部分 add 的场景。
