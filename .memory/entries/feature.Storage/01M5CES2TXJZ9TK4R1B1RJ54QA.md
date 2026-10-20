---
id: 01M5CES2TXJZ9TK4R1B1RJ54QA
module: feature.Storage
entity: ChangedSince
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/vcs/base.py#VCS.changed_since
- src/pmem/vcs/git.py#changed_since
- src/pmem/vcs/svn.py#changed_since
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 版本库按秒返回改动与提交时刻，供严格的过期判定使用
aliases:
- changed_after
- 改动时间
---
需求来源：负责人要求过期检查必须严格（2026-10-20），过期判定需要精确到秒的改动时间。

必须保持的行为：
- 版本库适配层按 Unix 秒返回改动时刻（changed_since）、每个文件的提交时刻列表（commit_times）和某时刻的旧版文件（file_before），不要退回按天的接口。
- 未提交的修改按文件修改时间算；已删除的文件按当前时刻算。
- 未纳入版本库的文件不报改动（Unity 工程 mtime 误报多）。
- 路径参数按 path_batches 分批，Windows 命令行过长时不能静默变成“都没改过”。

入口：src/pmem/vcs/base.py（接口与无版本库实现）、git.py、svn.py。
