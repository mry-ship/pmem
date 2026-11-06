---
id: 01M6RD5MPS1XRH27TD6X4ZJGM1
module: feature.Gate
entity: ShellParse
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell/constants.py
- src/pmem/hooks/shell/targets.py#_script_of
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 带小版本号的 python3.12 事前不会被当成解释器
verify: python3.12 script.py 时 _script_of 为 None；python.exe 完整路径仍能认出
applies: 闸门事前解析终端命令里的脚本写入
---
doctor 已把 python3.12、python3.11.exe 当成控制台解释器告警，但闸门的 _INTERPRETERS / _LAUNCHERS 仍是精确集合：python、python3、py、node、deno。

python3.12 script.py 或 python3.11.exe script.py 的 _program 是 python3.12 / python3.11，不在集合里。
_script_of 返回 None，事前 scan 不会去读脚本里的写入路径，这条命令只靠执行后的快照比对。
快照当天因仓库太大被暂停、或列未提交文件失败时，这次写入不会被事前拦住。

C:\Python312\python.exe 会去掉目录和 .exe，变成 python，仍然认得出。漏的是带小版本号的解释器名，和 doctor 刚补上的那类名字正好错开。
