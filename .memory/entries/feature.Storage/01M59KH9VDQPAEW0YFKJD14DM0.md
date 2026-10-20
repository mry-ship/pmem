---
id: 01M59KH9VDQPAEW0YFKJD14DM0
module: feature.Storage
entity: History
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/vcs/base.py#commits_since
- src/pmem/vcs/git.py#commits_since
- src/pmem/vcs/svn.py#commits_since
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 提交历史
- 热度扫描
- git log
- svn log
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：读取提交历史（给热度扫描用）改由版本库适配器提供：VCS.commits_since(since) 返回 [(提交日期, [相对路径...])]，基类返回空，Git 用 git log --since --name-only --relative，SVN 用 svn log -v --xml（最多 2000 条，按仓库相对 URL 去前缀）。
两者都带 HISTORY_TIMEOUT（120 秒），超时或 XML 解析失败返回空列表。

原因：原先 scan/lite.py 自己拼 git/svn 命令，绕过了配置里的 vcs 设置和适配器，新增版本库类型要改两处。现在加一种版本库只需实现适配器。

影响：sync、seed、report 的热度都经传入的 vcs 读取，sync 与存储共用同一个适配器实例。风险：SVN 大仓库超过 2000 条提交时早期热度会偏低。
