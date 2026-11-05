---
id: 01M6N9HK5R9GRD6C1SEZZKXSZ3
module: feature.Onboarding
entity: WindowsConsole
kind: conclusion
status: active
supersedes: []
anchors: []
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: 出图仍弹：Agent Shell 写 python，靠 pre-shell 改成 pyw
verify: ensure_cursor_stubs 后 hooks.json 含 art_shell_hook；echo python 命令 | pyw -3
  -u art_shell_hook.py 返回 updated_input
applies: Windows + Cursor-Pmem-Art 出图/Shell
aliases:
- pre-shell改写
verified: '2026-11-05'
verified_at: '2026-11-05T16:00:41.825+08:00'
---
现场：Art transcript 大量 Shell 仍是 python pmem_art.py / python image_gen.py，只改文档与 hooks 启动器不够。
根治：Windows preToolUse matcher=Shell 跑轻量 art_shell_hook.py（~90ms），用 updated_input 把 python/python3/py -3 改成 pyw -3 -u。
不用 pmem_art.py hook（冷启动十几秒）。
验证：重开 Art 窗后 hooks 含 art_shell_hook；
出图时 Cursor hooks 日志里 Shell command 应变 pyw；黑框应停。
