---
id: 01M5ENK61221Y0NXRMRQA0ZMJK
module: feature.Gate
entity: ShellParse
kind: risk
status: active
supersedes:
- 01M5ENJPMAY12Q3NSTNJSSE84X
anchors:
- src/pmem/hooks/shell.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 执行前后快照会把并行对话改的文件算到本对话命令头上，只读对话也被要求补写记忆
aliases:
- 误报
- 并行对话
- 快照比对
---
风险：终端命令走执行前后快照比对时（认不出写目标的命令，如 cmd /c、uv run python 脚本，连 uv run pmem record --help 也会），快照只比工作区未提交文件，分不清是谁改的。

现象（2026-10-21 实测）：本对话只跑了 git log/show、导出旧版本到临时目录、pmem record --help 这类只读命令，期间另一个对话在改 src/pmem/cli/brief.py、hooks/memories.py、core/registry.py。
Hook 每次都提醒“刚才的终端命令改了 xxx，属于 infra.Common / feature.Gate / feature.ModuleCatalog”，回合结束还要求给这些模块补写功能记录。

影响：同一工作区并行开多个对话时，只读的对话也会被要求补查、补写记忆；照做会写出与本对话无关的功能记录，也会让闸门把没查过的模块误判为已编辑。
应对：收到这类提醒先确认本对话的命令本身是否只读、是否真的改过这些文件；没改就回复无需记录，不要编功能记录。
