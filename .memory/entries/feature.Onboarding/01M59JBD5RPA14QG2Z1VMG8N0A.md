---
id: 01M59JBD5RPA14QG2Z1VMG8N0A
module: feature.Onboarding
entity: Scan
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/vcs/git.py#commits_since
- src/pmem/generate/templates.py#CONSOLIDATE_SKILL
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 热度为空
- 子目录项目
- monorepo
- 提交历史取不到
verified: '2026-10-27'
verified_at: '2026-10-27T17:33:08.864+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正：轻量扫描统计修改热度时，git log --name-only 输出的是相对仓库根目录的路径。
项目在仓库子目录里（monorepo 或客户端放在 client/ 下）时全部对不上，热度为空，sync 和模块划分建议当作“没有历史”。
现在加 --relative，按项目目录输出。
另：生成的 pmem-consolidate 技能模板补充了 migrate move（把归错模块的记忆按 id 搬走）和 anchors --rename（代码搬家后批量改关联代码）两步。
