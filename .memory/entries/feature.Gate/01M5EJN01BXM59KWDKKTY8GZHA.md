---
id: 01M5EJN01BXM59KWDKKTY8GZHA
module: feature.Gate
entity: ShellParse
kind: risk
status: active
supersedes:
- 01M51YSZGCTE8VTY010YN58PMZ
- 01M59JGGE104VESC7EX3D0TGNF
anchors:
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/shell.py#may_change_unseen
- src/pmem/hooks/snapshot.py#_shell_after
- src/pmem/hooks/snapshot.py#_snapshot_before_shell
- src/pmem/hooks/snapshot.py#_dirty_snapshot
- src/pmem/hooks/snapshot.py#_only_committed
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 认不出写目标时靠执行前后快照比对兜底，只能提醒拦不住；提交不算修改
aliases:
- 快照比对
- 误报修改
---
结论：事前解析认不出写目标的终端命令，闸门靠“执行前后未提交文件快照比对”兜底；它只能提醒、拦不住（命令已执行完）。

触发：命令在跑脚本或内联代码、目标里有变量、含通配符，或含不认识的程序（格式化工具、git stash/reset、patch、构建、ForEach-Object 脚本块、find -delete、管道下游的删除/移动等；只读命令和认出了目标的写命令除外）。

做法：执行前后各取一次快照（Git 用 git ls-files -m -d -o，SVN 用 svn status --xml；Hook 多约 70 毫秒）。
- 快照按命令摘要分开存，并行命令互不覆盖；命令被拒绝时不存；只剩一个待处理快照时当前命令也需要快照才借用。
- 改动的文件记为已编辑；改到没查过的有记忆模块时立即用 additional_context 提醒补查。同一时段编辑工具（afterFileEdit 记录过的文件）改的不算到命令头上。
- 执行后快照取不到时整次跳过，不能拿空快照比（否则之前所有未提交文件都会被当成本命令改的）。
- 提交不算修改：文件不在执行后快照里、但仍存在且修改时间和大小与之前相同，说明是被提交了（2026-10-19 曾把 git commit 误报成“改了 migrate.py”）；被删掉或被 git checkout 还原的仍算。
- 单次快照超过 1 秒写 snapshot-slow 标记，24 小时内不再取快照，hooks 事件日志记 snapshot_slow。

风险：无版本库项目没有这一层；超大仓库触发暂停后 24 小时内失效。合并自 2 条记忆。
