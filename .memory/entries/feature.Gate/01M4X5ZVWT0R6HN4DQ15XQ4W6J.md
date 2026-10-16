---
id: 01M4X5ZVWT0R6HN4DQ15XQ4W6J
module: feature.Gate
entity: State
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py#on_compact
revision: git:74edc08
author: 1002378395@qq.com
note_date: '2026-10-14'
verified: '2026-10-16'
---
闸门在两种情况下的实测行为：

1. 上下文压缩（preCompact）会清空本对话的 searched / warned，压缩后再改同一模块会再被拦一次。
   这是有意设计：压缩后 Agent 已丢失之前查到的记忆内容。
   排查“warn 档同一模块被拦两次”时先看 hooks 录制里两次拦截之间有没有 preCompact。

2. Agent 一次发出的多个编辑，Cursor 实际逐个执行，每个都单独走 preToolUse。warn 档只拦第一个，后面的直接放行，所以被拦的那一处修改需要 Agent 检索后重做，其余已生效；不要整批重发，否则会重复修改。

证据：本仓库自举时 service.py 三处并行修改只有第一处被拒；两次拒绝之间 20:06:01 有 preCompact 事件。
