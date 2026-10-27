---
id: 01M51NT866AKQ9RACAJ1E27H8D
module: feature.Gate
entity: SkipMarker
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/payload.py
- src/pmem/hooks/gate.py
revision: git:1acd957
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 跳过记忆
- 误判跳过
- skip_markers
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
根因：用户提问“如何避免单次问询 跳过记忆审查？”时，整个对话被当成“跳过记忆”。之后读代码不再附摘要，结束时也不提醒。

原因：skip_markers 原先按子串匹配；Cursor 在 Windows 上把 prompt 按 GBK 误解码，反解乱码后得到的原文仍然包含“跳过记忆”这几个字，于是会话状态里的 skip 被置为 true，并在整个对话中保持。

修正：标记必须作为独立短语出现。
紧跟的字符如果是字母、数字或汉字，就不算命中，语气词（吧了呀啊哈呢嘛）除外。
前 4 个字符里有否定或疑问词（不、别、勿、没、避免、防止、如何、怎么、是否），也不算命中。
原文和反解后的文本都找不到这个标记时，才退回模糊匹配。

证据：用当时抓到的真实 Hook 输入回放，修正前判为 skip，修正后不再命中。“跳过记忆”“跳过记忆吧”“这次跳过记忆，直接改”仍然命中。

影响：被误判的对话里，闸门、记忆审查、结束提醒全部失效，而且不会报错，很难察觉。排查时先看 sessions/<对话>.json 里的 skip 字段。
