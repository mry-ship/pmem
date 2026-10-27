---
id: 01M5YT0QHDFXQTVV540SF3P0B1
module: feature.Storage
entity: ChangedSince
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/vcs/git.py#GitVCS.changed_since
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: Git 的 changed_since 包含未跟踪且未被忽略的新文件
verify: uv run pytest tests/vcs/test_vcs.py::test_git_changed_since_includes_untracked_files_but_not_ignored_ones
applies: Git 仓库的 changed_since；SVN 不把未纳入版本库的文件算改动
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
需求来源：过期核对要看到还没 git add 的新文件，否则锚点指向它的记忆在第一次提交之前不会因需核实。
必须保持：Git 的 changed_since 在 git diff HEAD 之外，用 git ls-files --others --exclude-standard 列出请求路径里未跟踪的文件，按修改时间与 since 比较。
被忽略的文件不进结果。
写记忆之前就改好的未提交内容仍不算之后改过。
适用：过期核对、凡是走 changed_since 的调用。SVN 仍不报未纳入版本库的文件。
