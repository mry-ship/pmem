---
id: 01M6R9WC3RH7DRARWJ2EW0J3GZ
module: feature.Gate
entity: ShellParse
kind: correction
status: active
supersedes:
- 01M6R7JH10J0SWWP76GTSKR01J
anchors:
- src/pmem/hooks/shell/targets.py
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 旧 shell.py 锚点已迁到 shell/ 包，不再整批报已不存在
---
已修：记忆锚点与 path_queries.yaml 已改到 shell/targets.py、shell/lexer.py 等真实文件；符号级锚点抽查均能解析。拆包后不再因 shell.py 缺失整批报「已不存在」。
