---
id: 01M51WPJDDJDA2KXGTHK7YVFV0
module: feature.Gate
entity: ShellParse
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell.py#scan
- src/pmem/hooks/shell.py#cli_args
- src/pmem/hooks/gate.py#Gate.vcs
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 命令解析
- 终端解析
- shell.py
- Hook启动
---
决定：终端命令解析（写到哪些文件、是否在跑脚本或内联代码、嵌套 powershell/cmd/bash、命令里的 pmem search/graph/record 参数、输出是否被丢弃）从 gate.py 拆到 src/pmem/hooks/shell.py，gate.py 只保留闸门、审查和提醒逻辑，行为不变。
gate.py 仍重新导出 cli_args、shell_write_targets，测试和外部调用不用改；
改命令识别规则去 shell.py。
同时为缩短 Hook 启动，gate 里的版本库适配（detect_vcs，约 12 毫秒）改为用到时才导入（只有过期核对和终端命令前后比对需要）。
配合配置解析缓存，钩子进程导入耗时从约 100 毫秒降到约 38 毫秒；
不涉及模块的 post-tool 约 0.17 秒，改前拦截（deny，含过期核对缓存命中）约 0.30 秒。
