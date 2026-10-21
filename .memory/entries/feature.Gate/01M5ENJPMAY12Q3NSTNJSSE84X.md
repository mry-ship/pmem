---
id: 01M5ENJPMAY12Q3NSTNJSSE84X
module: feature.Gate
entity: ShellParse
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 执行前后快照会把别的对话同时改的文件算到本对话命令头上，触发误报和补写功能记录提醒
aliases:
- 误报
- 并行对话
- 快照比对
source:
  conversation: 4762f3ef-90e0-4867-bd54-88918442d890
---
风险：终端命令走执行前后快照比对时（认不出写目标的命令，如 cmd /c、uv run python 脚本），快照只比工作区未提交文件，分不清是谁改的。

现象（2026-10-21 实测）：本对话只跑了 git log/show 和把旧版本导出到临时目录的只读命令，期间另一个对话在改 src/pmem/cli/brief.py、src/pmem/hooks/memories.py；
Hook 立即提醒“刚才的终端命令改了 brief.py，属于 infra.Common”，回合结束又要求为 infra.Common、feature.Gate 补写功能记录。

影响：同一工作区并行开多个对话时，只读的对话也会被要求补查、补写记忆；Agent 若照做会写出与本对话无关的功能记录。
应对：收到这类提醒先确认本对话是否真的改过这些文件（命令本身是否只读），没改就回复无需记录，不要编功能记录。
可能的改进方向：结合 afterFileEdit 以外的会话归属信息或命令写目标白名单，目前未做。
