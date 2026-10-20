---
id: 01M4ZFGEJP67VZSZ85VY13T2DT
module: feature.Storage
entity: ChangedAfter
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/vcs/svn.py#changed_after
- src/pmem/vcs/git.py#changed_since
revision: git:fc9f6d8
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- 改动日期
- 未纳入版本库
- unversioned
- 慢
verified: '2026-10-19'
---
结论：用 svn info 批量查文件的最后提交日期时，只要目标里有一个路径未纳入版本库（unversioned，例如 TileMatch 的 Assets/MonopolyGame 整个目录是“?”），命令就会以退出码 1 结束（E200009，并带 W155010 “node not found” 警告）。
但 stdout 里其余路径的 XML 仍然完整输出，可以直接解析。

原先的做法是批量失败就逐个文件查询。TileMatch 上 190 个关联文件要 6.1 秒（检索变慢、卡顿）；改为解析部分输出后只要 0.28 秒，得到的改动文件同为 95 个，日期一致。svn status 同样按部分输出解析。

其他要点：
- svn info 只读本地工作副本元数据，不访问服务器。commit/date 是 UTC 时间，取前 10 位作为日期。
- 本地有修改（modified / replaced）的文件记为今天改过。
- 未纳入版本库的文件不报改动：这类文件只有 mtime 可看，而 Unity 工程的 mtime 误报很多，宁可漏报。
- Git 侧用一次 git log --since=<日期+1天> --format=@%cs --name-only --relative，再加 git diff HEAD --name-only --relative，取本地修改。
