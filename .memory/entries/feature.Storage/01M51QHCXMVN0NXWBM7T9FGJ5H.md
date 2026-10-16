---
id: 01M51QHCXMVN0NXWBM7T9FGJ5H
module: feature.Storage
entity: FileAt
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/vcs/git.py#file_at
revision: git:30e135f
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 历史版本
- 旧版文件
---
决定：版本库适配层提供“取某天那版文件内容”的能力，供按函数判断记忆是否过期。
Git 实现：先 `git rev-list -1 --before="<日期> 23:59:59" HEAD -- <路径>` 找到当天及之前最后一次改动该文件的提交，再 `git show <提交>:./<路径>` 取内容；
找不到提交或命令失败返回空。
SVN 和无版本库暂不支持（返回空），调用方据此退回按文件判断。

注意：路径要用 `./` 前缀相对当前目录解析，否则在子目录运行时会按仓库根解析错。结果按（路径, 日期）缓存在检查器里，同一次检索不会重复调 git。
