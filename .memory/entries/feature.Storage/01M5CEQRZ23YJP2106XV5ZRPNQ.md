---
id: 01M5CEQRZ23YJP2106XV5ZRPNQ
module: feature.Storage
entity: ChangedSince
kind: correction
status: active
supersedes:
- 01M4ZFGEJP67VZSZ85VY13T2DT
- 01M51QHCXMVN0NXWBM7T9FGJ5H
anchors:
- src/pmem/vcs/git.py#changed_since
- src/pmem/vcs/git.py#commit_times
- src/pmem/vcs/git.py#file_before
- src/pmem/vcs/svn.py#commit_times
- src/pmem/vcs/svn.py#changed_since
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 改动时间与旧版文件接口精确到秒；SVN 未纳入路径时解析部分输出
verify: uv run pytest tests/vcs/test_vcs.py -k changed_since
aliases:
- changed_after
- file_at
- 改动日期
- 旧版文件
- unversioned
---
更正（替代 ChangedAfter、FileAt 两条）：版本库适配层查“文件何时改过”和“取旧版文件”的接口改为精确到秒（Unix 时间戳），供过期判定（AnchorChecker）使用。
原接口 changed_after(paths, 日期) / file_at(rel, 日期) 只到天，导致基准日当天之后的改动全部漏报，已删除。

现行接口（vcs/base.py，Git、SVN 覆盖）：
- changed_since(paths, since) → {路径: 最后一次改动时刻}：提交时间 + 未提交的修改（取文件修改时间，不再记为今天）；
- commit_times(paths, since) → {路径: [提交时刻，从早到晚]}：只算提交，用来找记忆文件写入后的第一次提交；
- file_before(rel, moment) → 该时刻已提交的文件内容，取不到返回 None。
没有版本库时按文件修改时间。

Git：git log --since=<带时区的 ISO 时间> --format=@%ct --name-only --relative，再加 git diff HEAD --name-only --relative 取本地修改；
file_before 用 git rev-list -1 --before=<ISO 时间> HEAD -- <路径>，再 git show <提交>:./<路径>（./ 让路径相对项目根，项目可能是仓库子目录）。
--since/--before 含边界那一秒；同一次提交里的记忆和代码时间相同，不算“之后改过”。

SVN（结论仍成立）：svn info 批量查最后提交时间时，只要有一个路径未纳入版本库，命令就以退出码 1 结束（E200009，带 W155010），
但 stdout 里其余路径的 XML 仍完整，直接解析部分输出（TileMatch 190 个文件从逐个查询的 6.1 秒降到 0.28 秒）；svn status 同理。
svn info 只读本地元数据，不访问服务器；commit/date 是 UTC 时间，现在完整解析到秒。
SVN 的 commit_times 只有最后一次提交（取完整历史要走服务器），所以 SVN 下记忆文件被再次提交后，基准仍会顺延到那次提交。
未纳入版本库的文件不报改动：Unity 工程的 mtime 误报很多，宁可漏报。
路径参数仍按 path_batches 每批 8000 字符分批（Windows 命令行上限）。
