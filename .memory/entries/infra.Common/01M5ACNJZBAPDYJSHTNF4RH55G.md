---
id: 01M5ACNJZBAPDYJSHTNF4RH55G
module: infra.Common
entity: SeenHandoff
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/core/seen.py#claim_handoff
- src/pmem/core/seen.py#note_handoff
- src/pmem/cli/main.py#build_parser
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
summary: 终端检索认领对话交接后不删除记录，靠 120 秒窗口过期
aliases:
- 交接
- handoff
- 对话id
- 终端检索
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
---
排除：终端 pmem search 认领交接记录后不删除。
背景：终端里的 pmem search 拿不到对话 id。
Hook 在命令执行前把“对话 id + 要查的模块”写进缓存目录 seen/cli-handoff.json（保留最近 8 条），命令行在 120 秒内按模块认领最近一条；
全局检索（没给模块）只认领没登记模块的记录。
不删除的原因：同一对话常连续查同一模块，每条命令 Hook 都会重新登记，删了反而让第二次检索拿不到对话 id；窗口过期自然失效。
已知代价：两个对话恰好同时在终端查同一模块时可能认错对话，后果只是对方少显示几条正文（可用 --full 取回）。
去重记录 seen/<对话>.txt 一行一个 id，追加写，7 天过期，在 stop 时清理。
命令行同步新增 search --full，record --summary / --verify / --scope。
