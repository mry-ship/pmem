---
id: 01M5YT0PZFD2WQ2GVTK21K9TJV
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes:
- 01M5YS5RQQ5B5KJ7068A9AJPWG
anchors:
- src/pmem/vcs/git.py#GitVCS.changed_since
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: Git 未跟踪且未忽略的新文件按修改时间标需核实
verify: uv run pytest tests/vcs/test_vcs.py -k "untracked or local_edits or precise_to_the_second"
applies: Git 仓库；锚点文件从未被跟踪、且没被 gitignore 排除时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
更正：锚点指向从未被 Git 跟踪的新文件时，这个文件后来改了也会标需核实。
原先 GitVCS.changed_since 只用 git diff HEAD --name-only，未跟踪文件不在结果里，过期核对会漏掉它。
现在同一批路径再跑 git ls-files --others --exclude-standard，按文件修改时间与基准比较：写记忆之前就改好、还没提交的不算之后改过。
被忽略的文件仍不报。
仍成立：SVN 未纳入版本库的文件不报改动（工程目录 mtime 误报很多，宁可漏报）。已跟踪文件的未提交修改仍走 diff HEAD。
