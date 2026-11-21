---
id: 01M7Z1TCXGZJHWC18PW445B793
module: feature.Gate
entity: SpecRead
kind: feature
status: active
supersedes:
- 01M5M2X26PNS3D45NPQMFV9A59
anchors:
- src/pmem/hooks/guard.py#_guard_spec
- src/pmem/hooks/guard.py#_harvest_spec_reads
- src/pmem/hooks/gate.py
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 改代码前默认要读已写完的程序设计和模块现状
verify: uv run pytest tests/hooks/test_gate.py -q -k 'spec_read or empty_spec or transcript_read
  or glob_ or symlink or memory_gate or grep_pattern or writing_the_spec or shell_with_several
  or pre_tool_edit'
applies: spec.read_before_edit 为真且闸门不是 off、本对话未跳过记忆时
source:
  conversation: 5500e8d7-007c-460c-b7d7-15a5bb04aee9
---
需求来源：用户要求修改前读取相关规格默认开启。
必须保持：程序设计或模块现状已写完（没有整行空标记，行尾 CR 仍算）时，block 在本对话读过之前拦住修改。
读过只认查看工具：Read、Grep、Glob 的 post-tool，对话记录里这些工具的调用，打开模块规格目录，Glob 模式点名该目录。
写或改规格文件（pre-tool 或 post-tool）不算读过；同一次写入同时列出规格路径和代码路径也不算。拦截当下这次写入时，不要把当前工具参数里的路径记成已读。
指向项目内的符号链接仍要读，指出项目外的不读。
空骨架、文件不存在、只写策划或美术不拦。
warn 只拦一次。
闸门 off 或跳过记忆不拦。
同一次修改盖住多个模块或多个文件（含 Shell 多个写入目标、通配展开）时，先返回记忆闸门，同一条里不提规格。
Cursor 对话记录不含工具调用，quiet 和 Codex 的 Hook 看不到 Read。本对话还没记到过任何一次读取时，第一次拦住把规格摘录放进提示，再改放行，避免一直拦。已经记到过读取之后，没读完的文件继续拦。
规格提醒缺省改为开。仍成立：与功能记录用同一份改了行为的模块名单；声明无需记录、只改免记录文件、已写过四份正文之一的不提醒；目录里还没有美术设计.md 时补上这一份；每条以 [pmem] 开头。
入口：改代码前的 pre-tool 闸门。
