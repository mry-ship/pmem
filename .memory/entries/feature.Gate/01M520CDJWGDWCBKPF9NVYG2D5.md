---
id: 01M520CDJWGDWCBKPF9NVYG2D5
module: feature.Gate
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- sessionStart
- 新对话
- hook事件
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
---
决定：pmem hook 命令的事件列表增加 session，对应 Cursor 的 sessionStart（新对话开始时触发一次）。
装了 pmem 时闸门对该事件什么都不做（返回 {}），它的作用在包装脚本 .memory/bin/pmem-hook 里：找不到 pmem 时由脚本直接返回提示，让 Agent 告诉用户安装 pmem。

影响范围：只影响 hooks.json 里新增的 sessionStart 一项；其他事件不变。

风险：队友本机的 pmem 版本比项目里的 hooks.json 旧时，pmem hook session 会因不认识该事件报参数错误；
Cursor 按 failClosed=false 放行，不会卡住，但会在 hook 错误日志里留记录，升级 pmem 即可。
