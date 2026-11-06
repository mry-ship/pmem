---
id: 01M6R7JH10J0SWWP76GTSKR01J
module: feature.Gate
entity: ShellParse
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell/__init__.py
- src/pmem/index/anchors.py#_read_anchor
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: shell.py 拆成包后旧锚点会整批报「已不存在」
verify: AnchorChecker 对 src/pmem/hooks/shell.py#scan 应不再报已不存在（锚点已迁到 shell/*.py 或保留
  shim）
---
0.6.4 把 hooks/shell.py 拆成 shell/ 包后，磁盘上不再有 shell.py。
锚点核对按「路径必须是真实文件」判断，不会把 shell/__init__.py 当成 shell.py。
本库约 24 条记忆和 tests/fixtures/eval/path_queries.yaml 仍指向 src/pmem/hooks/shell.py，检索/摘要会整批标「需核实：已不存在」，符号级核对也失效。
拆文件或改名时必须同步改锚点（或留一层 shim 文件），并跑一遍 path_queries / pmem anchors。
