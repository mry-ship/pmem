---
id: 01M5YS5RQQ5B5KJ7068A9AJPWG
module: feature.Retrieval
entity: StaleCheck
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/vcs/git.py#changed_since
- src/pmem/index/anchors.py#AnchorChecker._check
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 从未提交的新文件改了也不会标需核实
verify: 新建未 git add 的文件，写一条锚点指向它的记忆，再改函数体；search_memory 该条不应出现 stale，直到该文件被提交
applies: Git 仓库；锚点文件从未被跟踪时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
现象：锚点指向从未被 Git 跟踪的新文件时，这个文件随后再改，记忆不会标 stale。文件一旦进入提交，之后的未提交修改能标出。
原因：GitVCS.changed_since 用 git diff HEAD --name-only 找未提交改动，这条命令不列出未跟踪文件。
过期核对只对 changed_since 返回的路径比较函数块。
缓存指纹 dirty_files 用了 git ls-files -o，未跟踪文件一变缓存会失效，但重算结果仍是“没改过”。
影响：对还没纳入版本库的新文件写下的记忆，在第一次提交之前不会因为代码变了而要求核对。已跟踪文件的未提交修改不受影响。
证据：src/pmem/vcs/git.py changed_since；index/anchors.py AnchorChecker._check。
