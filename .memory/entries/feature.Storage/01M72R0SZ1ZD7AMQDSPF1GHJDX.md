---
id: 01M72R0SZ1ZD7AMQDSPF1GHJDX
module: feature.Storage
entity: HistorySince
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/vcs/base.py#history_since
- src/pmem/vcs/git.py#history_since
revision: git:dbfdab4
author: 1002378395@qq.com
note_date: '2026-11-10'
summary: VCS.history_since 返回含提交说明的历史，供 harness 预算
verify: uv run pytest tests/vcs
---
需求：常一起改与修复提交统计需要提交说明。必须保持的行为：
- VCS.history_since(since) 返回 [(日期, 说明首行, 文件列表)]，新的在前；基类空列表。
- commits_since 仍为 [(日期, 文件列表)]；SVN 的 commits_since 委托 history_since，Git 两套各自实现。
入口：vcs/base.py、git.py、svn.py。
