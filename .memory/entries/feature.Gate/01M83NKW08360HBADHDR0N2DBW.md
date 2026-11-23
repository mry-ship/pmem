---
id: 01M83NKW08360HBADHDR0N2DBW
module: feature.Gate
entity: ShellParse
kind: risk
status: active
supersedes:
- 01M5EJN01BXM59KWDKKTY8GZHA
- 01M5ENK61221Y0NXRMRQA0ZMJK
anchors:
- src/pmem/hooks/shell/targets.py#scan
- src/pmem/hooks/shell/targets.py#may_change_unseen
- src/pmem/hooks/snapshot.py#_shell_after
- src/pmem/hooks/snapshot.py#_snapshot_before_shell
- src/pmem/hooks/snapshot.py#_dirty_snapshot
- src/pmem/hooks/snapshot.py#_only_committed
- src/pmem/hooks/shell/__init__.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 认不出写目标时只能事后快照提醒，拦不住
aliases:
- 快照
- 事后提醒
- Shell
source:
  kind: document
---
风险：认不出写目标的终端命令，闸门靠执行前后未提交文件快照兜底，只能事后提醒、拦不住。

触发：跑脚本或内联代码、目标含变量或通配、或不认识的程序（格式化、git stash/reset、patch、构建、cmd /c、uv run python，连 uv run pmem record --help 也会）。
只读命令和已认出目标的写命令除外。
Git 用 git ls-files，SVN 用 svn status。
执行后快照取不到则整次跳过，不能拿空快照比。
提交不算修改（文件仍在且 mtime/大小不变）。
单次超过 1 秒则 24 小时内暂停快照。
无版本库没有这一层。

并行对话：快照只比工作区未提交文件，分不清是谁改的。只读对话也可能被提醒「刚才的命令改了别的模块」。先确认本对话命令是否真的改过；没改就回复无需记录，不要编功能记录。

合并自 2 条风险。认得出的写目标规则仍是同议题结论。
