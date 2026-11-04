---
id: 01M6JWSX408C9DEAENZNCVK3TE
module: feature.Onboarding
entity: Scan
kind: correction
status: active
supersedes:
- 01M59JBD5RPA14QG2Z1VMG8N0A
anchors:
- src/pmem/vcs/git.py#commits_since
- src/pmem/generate/templates.py#CONSOLIDATE_SKILL
revision: git:cef5279
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: git log 路径相对仓库根；项目在子目录时热度要对齐根路径
verified: '2026-11-04'
verified_at: '2026-11-04T17:04:24.128+08:00'
---
更正：轻量扫描统计修改热度时，git log --name-only 输出的是相对仓库根目录的路径。
项目在仓库子目录里（monorepo 或客户端放在 client/ 下）时全部对不上，热度为空，sync 和模块划分建议当作“没有历史”。
现在加 --relative，按项目目录输出。
另：生成的 pmem-consolidate 技能模板补充了 migrate move（把归错模块的记忆按 id 搬走）和 anchors --rename（代码搬家后批量改关联代码）两步。
