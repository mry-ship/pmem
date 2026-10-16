---
id: 01M51YSZGCTE8VTY010YN58PMZ
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes:
- 01M51VMZYT0266DSKQ153E41QQ
- 01M51WPJDDJDA2KXGTHK7YVFV0
anchors:
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/shell.py#may_change_unseen
- src/pmem/hooks/gate.py#_shell_after
- src/pmem/hooks/gate.py#_snapshot_before_shell
- src/pmem/hooks/gate.py#_dirty_snapshot
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 绕过
- 漏拦
- 误拦
- 终端写文件
- 快照
- bypass
---
结论：闸门识别终端写文件分“事前解析”和“事后比对”两层，解析规则集中在 src/pmem/hooks/shell.py，gate.py 只管拦截和提醒。

事前解析认得出：重定向、PowerShell 写文件命令、sed -i / perl -pi、tee、删除、复制移动、git checkout/restore/rm/mv/apply（checkout 不带 -- 时只认工作区里存在的文件）、[IO.File]::Write*、套一层的 powershell -Command/-File、cmd /c、bash -c 和直接运行的脚本（递归最多 3 层），以及 python/node 代码里写文件时的字面路径。先 cd / Set-Location 再写相对路径时按切换后的目录算。here-string（@' '@）和 heredoc 的正文当作数据，不再误拦；token 尾部的逗号、分号会去掉（曾把 `a.py",` 归到错误模块）。按 ; 拆语句会把引号里的命令拆开，两半各自仍能识别，不要改成严格的引号解析。

事后比对：命令在跑脚本或内联代码、目标里有变量，或含有不认识的程序（格式化工具、git stash/reset、patch、构建、ForEach-Object 脚本块、find -delete、从管道接收目标的 Remove-Item 等；只读命令和认出了目标的写命令除外）时，执行前后各取一次未提交文件快照（Git 用 git ls-files -m -d -o，SVN 用 svn status --xml；Hook 多约 70 毫秒）。快照按命令摘要分开存，并行命令互不覆盖；命令被拒绝时不存。改动的文件记为已编辑；改到没查过的有记忆模块时立即用 additional_context 提醒补查。同一时段编辑工具（afterFileEdit 记录过的文件）改的文件不算到命令头上。执行后快照取不到时整次跳过，不能拿空快照比（否则之前所有未提交文件都会被当成本命令改的）。单次快照超过 1 秒时写 snapshot-slow 标记，24 小时内不再取快照。

风险：事后比对只能提醒、拦不住（命令已经执行完）；无版本库项目没有这一层；超大仓库触发暂停后这一层在 24 小时内失效，hooks 事件日志记 snapshot_slow。合并自 3 条记忆。
